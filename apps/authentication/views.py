import os
from urllib.parse import urlsplit

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.http import Http404
from rest_framework import filters, generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Course, Institution, User, UserRole
from .notifications import send_notification
from .serializers import (
    ProfileSearchSerializer,
    PublicUserSerializer,
    UserProfileUpdateSerializer,
    UserSerializer,
)


class ProfileSearchPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50


class ProfileSearchView(generics.ListAPIView):
    """Busca compacta de perfis para a busca global do cabeçalho.

    Casa por nome (full_name) ou matrícula (registration_number) via SearchFilter
    (`?search=`). Retorna só nome, papel legível (Estudante/Professor) e
    instituição — o suficiente para a linha de resultado e o link /perfil/{matricula}.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = ProfileSearchPagination
    serializer_class = ProfileSearchSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['full_name', 'registration_number']

    def get_queryset(self):
        return (
            User.objects.select_related('institution')
            .filter(is_active=True)
            .order_by('full_name')
        )


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

        # O /api/rh/meus-dados/ aninha os dados de identidade em "vinculo"
        # (nome completo, campus, curso, currículo lattes). Mantemos fallback
        # para os campos planos do schema antigo (/api/rh/eu/, v2) caso a
        # SUAP_USER_INFO_URL aponte para outro endpoint.
        vinculo = suap_data.get("vinculo") or {}

        # --- APLICAÇÃO DE REGRAS DE NEGÓCIO & BUSCA ACADÊMICA ---

        # Schema atual expõe "tipo_vinculo" ("Aluno"/"Servidor"); o antigo, "tipo_usuario".
        tipo_usuario = str(suap_data.get("tipo_vinculo") or suap_data.get("tipo_usuario") or "").lower()

        # Variáveis acadêmicas para alunos iniciam vazias
        ira_aluno = None
        periodo_aluno = None
        curso_nome = None

        # Variável para curriculo lattes, caso seja professor
        lattes_url = None

        # Identidade suplementar para servidor/docente. O "vinculo" de servidor no
        # /meus-dados/ tem forma diferente do de aluno (cargo/categoria em vez de
        # nome/campus), então o nome completo e o campus podem não vir ali. O
        # /api/rh/eu/ tem schema plano e uniforme (nome_registro, campus) para
        # qualquer tipo de usuário e serve de fallback. Fica {} para alunos.
        eu_data = {}

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

        elif "servidor" in tipo_usuario or "docente" in tipo_usuario or "professor" in tipo_usuario:
            user_role = UserRole.TEACHER

            # O currículo Lattes pode vir aninhado no "vinculo" do /meus-dados/.
            lattes_url = vinculo.get("curriculo_lattes")

            # Busca nome completo e campus no /api/rh/eu/ (schema plano), pois o
            # "vinculo" de servidor não segue o mesmo formato do de aluno.
            eu_response = requests.get("https://suap.ifrn.edu.br/api/rh/eu/", headers=headers)
            if eu_response.status_code == 200:
                eu_data = eu_response.json()

        else:
            return Response(
                {"error": f"Acesso negado. A plataforma é restrita a professores e alunos. Seu perfil: {tipo_usuario}"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # --- SINCRONIZAÇÃO DAS CHAVES ESTRANGEIRAS ---

        # Busca ou cria a Instituição (Campus)
        instituicao_obj = None
        campus_nome = vinculo.get("campus") or eu_data.get("campus") or suap_data.get("campus")
        if campus_nome:
            instituicao_obj, _ = Institution.objects.get_or_create(name=campus_nome)

        # Busca ou cria o Curso
        curso_obj = None
        if curso_nome:
            curso_obj, _ = Course.objects.get_or_create(name=curso_nome)

        # --- FOTO DE PERFIL (SUAP) ---
        # Preferimos a foto de maior resolução (150x200); caímos para a 75x100 e,
        # por fim, para o campo "foto" plano (schema antigo). O SUAP pode devolver
        # caminho relativo (/media/...) ou URL absoluta; normalizamos para absoluta.
        foto_suap = (
            suap_data.get("url_foto_150x200")
            or suap_data.get("url_foto_75x100")
            or suap_data.get("foto")
            or eu_data.get("foto")
        )
        if foto_suap and foto_suap.startswith("/"):
            partes = urlsplit(user_info_url)
            foto_suap = f"{partes.scheme}://{partes.netloc}{foto_suap}"

        # --- SALVAR OU ATUALIZAR O USUÁRIO ---

        identificacao_suap = suap_data.get("matricula") or suap_data.get("identificacao")

        # Usamos update_or_create para sempre atualizar ira e períodos a cada login
        user, created = User.objects.update_or_create(
            registration_number=identificacao_suap,
            defaults={
                "username": identificacao_suap,
                "cpf": suap_data.get("cpf"),
                "email": suap_data.get("email")
                or eu_data.get("email_preferencial")
                or eu_data.get("email_academico")
                or eu_data.get("email"),
                "first_name": suap_data.get("nome_usual") or suap_data.get("primeiro_nome"),
                "full_name": vinculo.get("nome")
                or eu_data.get("nome_registro")
                or eu_data.get("nome")
                or suap_data.get("nome")
                or suap_data.get("nome_usual"),
                "image": foto_suap,
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

            # Notificações vivem no notification-service: criamos via chamada
            # interna (best-effort — falha não interrompe o login).
            send_notification(
                user_id=user.id,
                title=welcome_title,
                message=welcome_msg,
                notification_type="system",
            )

        # Gerando o nosso próprio JWT
        # Claims extras (role/email) embarcados no token para que os demais
        # serviços validem localmente pelo header, sem chamar o auth.
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email or ""
        # is_staff/admin viaja no token para que serviços downstream (ex.: feed)
        # possam distinguir publicações "do sistema" (ATLAS) das dos usuários.
        refresh["is_staff"] = user.is_staff

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "full_name": user.full_name,
                    "registration_number": user.registration_number,
                    "image": user.image,
                    "role": user.role,
                    "is_new_user": created,
                },
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


class DebugSetRoleView(APIView):
    """[DEMO] Alterna o papel do usuário autenticado entre professor e estudante.

    Existe apenas para apresentar funcionalidades restritas a docentes. A rota
    só é montada quando a flag ``DEMO_TOOLS_ENABLED`` (env ATLAS_DEMO_TOOLS) está
    ligada (ver urls.py); o guard abaixo é uma segunda barreira caso a rota seja
    exposta por engano — do contrário responde 404.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not settings.DEMO_TOOLS_ENABLED:
            raise Http404()

        raw = request.data.get("teacher")
        if isinstance(raw, str):
            teacher = raw.strip().lower() in ("true", "1", "yes", "on")
        else:
            teacher = bool(raw)

        user = request.user
        user.role = UserRole.TEACHER if teacher else UserRole.STUDENT
        user.save(update_fields=["role"])

        # Emite novos tokens já com a claim `role` atualizada, para que os demais
        # serviços validem o papel pelo header sem precisar chamar o auth.
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["email"] = user.email or ""

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class UserDetailView(APIView):
    """Resolve um usuário por matrícula (registration_number) ou por UUID (id).

    Substitui o antigo GetUserProfile do servidor gRPC (já removido): os
    serviços de tracks e scholarship guardam o usuário como UUID e precisam
    resolvê-lo pela API HTTP interna, enquanto o frontend costuma consultar
    pela matrícula. O mesmo endpoint aceita os dois formatos.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, matricula):
        lookup_value = (matricula or "").strip()

        # Cache do perfil (chave pelo valor consultado — matrícula OU id). O
        # signal post_save/post_delete do User invalida ambas as chaves quando
        # o usuário muda, então a resposta fica cacheada mas sempre correta.
        cache_key = f"user:{lookup_value}"
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        base_qs = User.objects.select_related("course", "institution")
        user = base_qs.filter(registration_number=lookup_value).first()
        if user is None:
            try:
                user = base_qs.get(id=lookup_value)
            except (User.DoesNotExist, ValidationError, ValueError):
                raise Http404("Usuário não encontrado por matrícula ou ID.")
 
        can_view_academic_data = (
            request.user.id == user.id
            or request.user.is_superuser
            or request.user.role == UserRole.TEACHER
        )
        serializer_class = (
            UserSerializer if can_view_academic_data else PublicUserSerializer
        )
        serializer = serializer_class(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InternalValidateView(APIView):
    """Endpoint interno usado pelo Nginx (auth_request) como barreira de
    autenticação na borda. Valida o JWT do header Authorization e, em caso
    de sucesso, devolve 200 com os headers X-User-Id e X-User-Role para o
    Nginx injetar nas requisições repassadas aos serviços downstream.

    Token ausente/inválido resulta em 401 automaticamente (IsAuthenticated).
    Não deve ser exposto publicamente — fica atrás do prefixo /api/auth/,
    chamado apenas internamente pelo gateway.
    """

    permission_classes = [IsAuthenticated]

    def _validate(self, request):
        resp = Response(status=status.HTTP_200_OK)
        resp["X-User-Id"] = str(request.user.id)
        resp["X-User-Role"] = request.user.role
        return resp

    # auth_request pode emitir a subrequisição com métodos variados;
    # respondemos a todos da mesma forma.
    def get(self, request):
        return self._validate(request)

    def post(self, request):
        return self._validate(request)

    def put(self, request):
        return self._validate(request)

    def patch(self, request):
        return self._validate(request)

    def delete(self, request):
        return self._validate(request)
