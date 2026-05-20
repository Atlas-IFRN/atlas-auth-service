import os
from datetime import timedelta

import requests
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Course, Institution, Notification, NotificationType, User, UserRole
from .serializers import NotificationSerializer, UserProfileUpdateSerializer, UserSerializer


class SuapLoginUrlView(APIView):
    permission_classes = [AllowAny]

    # Frontend chama essa view para obter a URL de login do SUAP e redirecionar o usuário para lá
    def get(self, request):
        suap_auth_url = os.getenv('SUAP_AUTHORIZATION_URL')
        client_id = os.getenv('SUAP_CLIENT_ID')
        redirect_uri = os.getenv('SUAP_REDIRECT_URI')

        # montando a URL de login do SUAP
        login_url = f"{suap_auth_url}?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"

        return Response({'login_url': login_url}, status=status.HTTP_200_OK)


class SuapCallbackView(APIView):
    permission_classes = [AllowAny]

    # O usuário volta do SUAP trazendo o code.
    def post(self, request):
        # Pegamos o code que o SUAP enviou
        code = request.data.get("code")
        if not code:
            return Response({'error': 'Código de autorização não fornecido'}, status=status.HTTP_400_BAD_REQUEST)

        # Preparamos os dados para solicitar o token de acesso ao SUAP
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": os.getenv('SUAP_REDIRECT_URI'),
            "client_id": os.getenv('SUAP_CLIENT_ID'),
            "client_secret": os.getenv('SUAP_CLIENT_SECRET'),
        }

        # Fazemos a requisição para obter o token de acesso do SUAP
        token_response = requests.post(os.getenv('SUAP_TOKEN_URL'), data=token_data)

        if token_response.status_code != 200:
            return Response({'error': 'Falha ao autenticar com o SUAP.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Pegamos o token de acesso da resposta
        access_token = token_response.json().get("access_token")

        # 1ª REQUISIÇÃO: Pedir os dados pessoais do usuário (RH)
        headers = {"Authorization": f"Bearer {access_token}"}
        user_info_url = str(os.getenv("SUAP_USER_INFO_URL")).strip()

        user_info_response = requests.get(user_info_url, headers=headers)

        if user_info_response.status_code != 200:
            return Response(
                {"error": f"Falha ao buscar dados no SUAP. Status: {user_info_response.status_code}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suap_data = user_info_response.json()

        # --- APLICAÇÃO DE REGRAS DE NEGÓCIO & BUSCA ACADÊMICA ---

        tipo_usuario = str(suap_data.get("tipo_usuario", "")).lower()

        # Variáveis acadêmicas para alunos iniciam vazias
        ira_aluno = None
        periodo_aluno = None
        curso_nome = None

        # Variável para curriculo lattes, caso seja professor
        lattes_url = None

        if "aluno" in tipo_usuario:
            user_role = UserRole.STUDENT

            # 2 REQUISIÇÃO: Buscar dados acadêmicos específicos do aluno
            edu_url = "https://suap.ifrn.edu.br/api/ensino/meus-dados-aluno/"
            edu_response = requests.get(edu_url, headers=headers)

            if edu_response.status_code == 200:
                edu_data = edu_response.json()
                ira_aluno = edu_data.get("ira")
                periodo_aluno = edu_data.get("periodo_referencia")
                curso_nome = edu_data.get("curso")

                if ira_aluno:
                    try:
                        ira_aluno = float(str(ira_aluno).replace(',', '.'))
                    except ValueError:
                        ira_aluno = None

        elif "docente" in tipo_usuario or "professor" in tipo_usuario:
            user_role = UserRole.TEACHER

            servidor_url = "https://suap.ifrn.edu.br/api/rh/servidores/"
            servidor_response = requests.get(servidor_url, headers=headers)

            if servidor_response.status_code == 200:
                servidor_data = servidor_response.json()
                lattes_url = servidor_data.get("curriculo_lattes")

        else:
            return Response(
                {"error": f"Acesso negado. A plataforma é restrita a professores e alunos. Seu perfil: {tipo_usuario}"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # --- SINCRONIZAÇÃO DAS CHAVES ESTRANGEIRAS ---

        # Busca ou cria a Instituição (Campus)
        instituicao_obj = None
        campus_nome = suap_data.get("campus")
        if campus_nome:
            instituicao_obj, _ = Institution.objects.get_or_create(name=campus_nome)

        # Busca ou cria o Curso
        curso_obj = None
        if curso_nome:
            curso_obj, _ = Course.objects.get_or_create(name=curso_nome)

        # --- SALVAR OU ATUALIZAR O USUÁRIO ---

        identificacao_suap = suap_data.get("identificacao")

        # Usamos update_or_create para sempre atualizar ira e períodos a cada login
        user, created = User.objects.update_or_create(
            registration_number=identificacao_suap,
            defaults={
                "username": identificacao_suap,
                "cpf": suap_data.get("cpf"),
                "email": suap_data.get("email_preferencial")
                or suap_data.get("email_academico")
                or suap_data.get("email"),
                "first_name": suap_data.get("nome_usual") or suap_data.get("primeiro_nome"),
                "full_name": suap_data.get("nome"),
                "role": user_role,
                "institution": instituicao_obj,
                "course": curso_obj,
                "ira": ira_aluno,
                "period": periodo_aluno,
                "lattes_url": lattes_url,
            },
        )

        if created:
            user.set_unusable_password()
            user.save()
            welcome_title = "Bem-vindo ao ATLAS! 🎓"
            if user_role == UserRole.STUDENT:
                welcome_msg = f"Olá {user.first_name}! Sua conta foi criada com sucesso. Explore todos os recursos da plataforma e boa sorte em seus estudos!"
            else:
                welcome_msg = f"Olá {user.first_name}! Sua conta foi criada com sucesso como professor. Bem-vindo ao ATLAS, sua plataforma de gestão acadêmica. Comece explorando os recursos disponíveis."

            Notification.objects.create(
                user=user, title=welcome_title, message=welcome_msg, type=NotificationType.SYSTEM
            )

        # Gerando o nosso próprio JWT
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {"id": user.id, "first_name": user.first_name, "role": user.role, "is_new_user": created},
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    # Apenas usuários autenticados podem acessar essa view para fazer logout
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # O frontend envia o refresh token para ser invalidado
            refresh_token = request.data.get("refresh")

            if not refresh_token:
                return Response(
                    {"error": "O refresh token é obrigatório para fazer logout."}, status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()  # Invalida o token para que não possa mais ser usado

            return Response({"message": "Logout realizado com sucesso."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            # Se o token já estiver na blacklist ou for inválido, cai aqui
            return Response({"error": "Token inválido ou já expirado."}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """Atualiza campos sociais (about_me, linkedin, github) do usuário atual."""
        user = request.user
        serializer = UserProfileUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, matricula):
        user = get_object_or_404(User, registration_number=matricula)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # filtro deslizante de 5 dias — recalcula a cada request, não na importação do módulo
        filtro_de_dias = timezone.now() - timedelta(days=5)
        qs = Notification.objects.filter(
            user=request.user,
            created_at__gte=filtro_de_dias,
        )

        is_read = request.query_params.get('is_read')
        if is_read is not None:
            qs = qs.filter(is_read=is_read.lower() in ('true', '1', 'yes'))

        type_filter = request.query_params.get('type')
        if type_filter:
            qs = qs.filter(type=type_filter)

        serializer = NotificationSerializer(qs.order_by('-created_at'), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationReadView(APIView):
    """PATCH /notifications/{id}/read/ — marca uma notificação como lida."""

    permission_classes = [IsAuthenticated]

    def patch(self, request, notification_id):
        notif = get_object_or_404(Notification, pk=notification_id, user=request.user)
        if not notif.is_read:
            notif.is_read = True
            notif.save(update_fields=['is_read'])
        return Response(NotificationSerializer(notif).data, status=status.HTTP_200_OK)


class NotificationMarkAllReadView(APIView):
    """POST /notifications/mark-all-read/ — marca todas as não lidas como lidas."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"updated": updated}, status=status.HTTP_200_OK)
