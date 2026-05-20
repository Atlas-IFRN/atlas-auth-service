import os
import sys
import concurrent.futures as futures
import grpc

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'proto'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django
django.setup()

from proto import user_pb2, user_pb2_grpc
from apps.authentication.models import User

class UserServicer(user_pb2_grpc.UserServiceServicer):
    def GetUserProfile(self, request, context):
        try:
            # Busca o usuário no banco pela matrícula fornecida
            user = User.objects.select_related('course', 'institution').get(matricula=request.matricula)
            
            # Monta a resposta binária mapeando os campos do Django para o Proto
            return user_pb2.UserResponse(
                id=str(user.id),
                matricula=user.matricula,
                first_name=user.first_name or "",
                full_name=user.full_name or "",
                email=user.email or "",
                role=user.role or "",
                ira=float(user.ira) if user.ira else 0.0,
                period=user.period or 0,
                about_me=user.about_me or "",
                linkedin=user.linkedin or "",
                github=user.github or "",
                curriculo_lattes=user.curriculo_lattes or "",
                course_name=user.course.name if user.course else "",
                institution_name=user.institution.name if user.institution else ""
            )
            
        except User.DoesNotExist:
            # Se o usuário não existir, avisa o outro serviço
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Usuário com a matrícula {request.matricula} não foi encontrado.")
            return user_pb2.UserResponse()

def serve():
    # Inicializa o servidor gRPC na porta interna 50051
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserServicer(), server)
    
    server.add_insecure_port('[::]:50051')
    print("🚀 Servidor gRPC do ATLAS Auth Service rodando na porta 50051...")
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()