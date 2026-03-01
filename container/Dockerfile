FROM public.ecr.aws/lambda/python:3.12

# Install deps needed for pyodbc + Microsoft ODBC driver
# NOTE: Lambda base image already has curl-minimal; installing curl conflicts.
RUN dnf -y update && \
    dnf -y install unixODBC unixODBC-devel gcc-c++ make && \
    curl -sSL https://packages.microsoft.com/config/rhel/9/prod.repo \
      > /etc/yum.repos.d/mssql-release.repo && \
    ACCEPT_EULA=Y dnf -y install msodbcsql18 && \
    dnf clean all

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY app.py ${LAMBDA_TASK_ROOT}

CMD ["app.lambda_handler"]