FROM python:alpine3.7

COPY example/app.py example/requirements.txt /
COPY flyte setup.py README.md /flyte/

RUN pip install -e /flyte

CMD [ "python", "./app.py" ]