import os
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings

from .models import User, UserRole, Institution, Course, Notification

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
                status=status.HTTP_400_BAD_REQUEST
            )

        suap_data = user_info_response.json()

        # --- APLICAÇÃO DE REGRAS DE NEGÓCIO & BUSCA ACADÊMICA ---
        
        tipo_usuario = str(suap_data.get("tipo_usuario", "")).lower()
        
        # Variáveis acadêmicas iniciam vazias
        ira_aluno = None
        periodo_aluno = None
        curso_nome = None

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

        elif "servidor" in tipo_usuario or "professor" in tipo_usuario:
            user_role = UserRole.TEACHER
        else:
            return Response(
                {"error": f"Acesso negado. A plataforma é restrita a professores e alunos. Seu perfil: {tipo_usuario}"}, 
                status=status.HTTP_403_FORBIDDEN
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
        
        # Usamos update_or_create para sempre atualizar notas e períodos a cada login
        user, created = User.objects.update_or_create(
            matricula=identificacao_suap,
            defaults={
                "username": identificacao_suap,
                "cpf": suap_data.get("cpf"),
                "email": suap_data.get("email_preferencial") or suap_data.get("email_academico") or suap_data.get("email"),
                "first_name": suap_data.get("nome_usual") or suap_data.get("primeiro_nome"),
                "full_name": suap_data.get("nome"),
                "role": user_role,
                "institution": instituicao_obj,
                "course": curso_obj,
                "ira": ira_aluno,
                "period": periodo_aluno,
            }
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
                user=user, 
                title=welcome_title, 
                message=welcome_msg,
                type="SYSTEM"
            )

        # Gerando o nosso próprio JWT
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "first_name": user.first_name,
                "role": user.role,
                "is_new_user": created 
            }
        }, status=status.HTTP_200_OK)