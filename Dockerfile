FROM python:3.10
WORKDIR /app
RUN pip install boto3
COPY a.py a.py
CMD [ "python3", "/app/a.py" ]
