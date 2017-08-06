FROM python:3.6.2-alpine

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY tooling.py .

CMD python tooling.py
