FROM python:3.8-slim-buster

RUN apt-get update
RUN apt-get install -y nginx python-psycopg2 postgresql

ENV PYTHONUNBUFFERED 1
ENV MIGRATE 0

# Set up Nginx

RUN addgroup --system nginx
RUN adduser --system nginx
RUN usermod -a -G nginx nginx
RUN mkdir -p /run/nginx

RUN mkdir -p /var/log/nginx && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stdout /var/log/nginx/error.log

COPY nginx.conf /etc/nginx/nginx.conf

COPY ./search_service /app
COPY ./requirements.txt /app
WORKDIR /app
RUN python3 -m pip install --upgrade pip
RUN pip3 install -r requirements.txt

COPY ./entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

CMD /entrypoint
