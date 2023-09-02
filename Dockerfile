FROM alpine:latest

RUN apk add --no-cache python3-dev py3-pip

RUN addgroup -S app && adduser -S app -G app
USER app

WORKDIR /home/app
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .

CMD ["python3", "src/main.py"]
