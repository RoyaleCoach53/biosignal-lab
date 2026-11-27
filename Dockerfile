FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /opt/biosignal
COPY pyproject.toml README.md LICENSE NOTICE.md /opt/biosignal/
COPY src /opt/biosignal/src
COPY app.py /opt/biosignal/app.py
COPY .streamlit /opt/biosignal/.streamlit
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    python -m pip install --no-cache-dir '.[all]' \
    && python -m pip check \
    && useradd --create-home --uid 10001 biosignal
RUN chmod -R a+rX /opt/biosignal
USER biosignal
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).read() == b'ok'"
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
