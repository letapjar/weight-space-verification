# The environment for training, playing and testing the networks, and for rebuilding the results tables.
# It is separate from code/docker/claude-code/Dockerfile, which is the sealed container the reader models ran in.
#
#   docker build -t weight-space .                                              # processor only
#   docker build -t weight-space --build-arg JAX_PACKAGE="jax[cuda12]==0.12.0.1" .   # NVIDIA GPU
#   docker run --rm weight-space                                                # runs the tests
#   docker run --rm --gpus all -it weight-space bash                            # a shell, in code/
FROM python:3.12-slim
ARG JAX_PACKAGE="jax==0.12.0.1"
WORKDIR /repo
COPY requirements-jax.txt .
RUN pip install --no-cache-dir "$JAX_PACKAGE" -r requirements-jax.txt
COPY . .
WORKDIR /repo/code
CMD ["python", "-m", "pytest", "-q", "jaxport", "test_readings.py"]
