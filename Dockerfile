# 1. Python 3.11.10 이미지를 사용하여 기반 이미지 설정
FROM python:3.11.10-slim

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 로컬 디렉토리의 requirements.txt 파일을 컨테이너로 복사
COPY requirements.txt .

# 4. requirements.txt에 정의된 라이브러리 설치
RUN pip install --no-cache-dir -r requirements.txt

# 5. Gradio 애플리케이션 파일을 컨테이너로 복사
COPY app.py .

# 6. ENV 파일을 컨테이너로 복사
# COPY .env.local .

# 7. Gradio 애플리케이션 실행에 사용할 포트 설정 (기본 7860 포트)
EXPOSE 7860
ENV GRADIO_SERVER_PORT=7860
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV AZURE_OPENAI_API_KEY="" \
    AZURE_OPENAI_ENDPOINT="" \
    AZURE_OPENAI_API_VERSION=""
    
# 8. Gradio 애플리케이션 실행 명령어 설정
CMD ["python", "app.py"]