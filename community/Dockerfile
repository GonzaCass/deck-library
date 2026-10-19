FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 COMMUNITY_DB=/data/community.sqlite3
RUN pip install --no-cache-dir gunicorn==26.2.0 && useradd --uid 10001 --create-home community && mkdir /data && chown community:community /data
WORKDIR /app
COPY deck_library /app/deck_library
COPY community /app/community
USER community
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=2)"
CMD ["gunicorn","--bind","0.0.0.0:8080","--workers","2","--threads","2","--timeout","45","community.server:application"]
