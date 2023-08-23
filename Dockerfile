FROM python:3.10.2
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BOT_PATH /opt/mod_mail_internal
WORKDIR $BOT_PATH
RUN apt update && apt install git -y
COPY ./requirements.txt .
RUN pip install --no-compile --no-cache-dir -r requirements.txt
RUN mkdir -p data/logs
COPY . .
CMD [ "python", "main.py" ]