import concurrent.futures as futures
import os
import sys

import grpc

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()

from apps.authentication.models import User
from apps.authentication.services.token_validator import validate_jwt
from proto import user_pb2, user_pb2_grpc


class UserServiceServicer(user_pb2_grpc.UserServiceServicer):
    def GetUserProfile(self, request, context):
        try:
            user = User.objects.select_related('course', 'institution').get(registration_number=request.matricula)

            return user_pb2.UserResponse(
                id=str(user.id),
                matricula=user.registration_number,
                first_name=user.first_name or "",
                full_name=user.full_name or "",
                email=user.email or "",
                role=user.role or "",
                ira=float(user.ira) if user.ira else 0.0,
                period=user.period or 0,
                about_me=user.about_me or "",
                linkedin=user.linkedin or "",
                github=user.github or "",
                curriculo_lattes=user.lattes_url or "",
                course_name=user.course.name if user.course else "",
                institution_name=user.institution.name if user.institution else "",
            )

        except User.DoesNotExist:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Usuário com a matrícula {request.matricula} não foi encontrado.")
            return user_pb2.UserResponse()


class AuthServiceServicer(user_pb2_grpc.AuthServiceServicer):

    def ValidateToken(self, request, context):
        payload = validate_jwt(request.token)

        if not payload:
            return user_pb2.ValidateTokenResponse(valid=False)

        return user_pb2.ValidateTokenResponse(
            valid=True,
            user_id=payload["sub"],
            role=payload["role"],
            email=payload["email"],
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserServiceServicer(), server)
    user_pb2_grpc.add_AuthServiceServicer_to_server(AuthServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    print("🚀 Servidor gRPC do ATLAS Auth Service rodando na porta 50051...")
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
