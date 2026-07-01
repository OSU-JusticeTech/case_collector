# Use the official high-performance uv image
FROM ghcr.io/astral-sh/uv:alpine

# Set the working directory
WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1

# Copy only the configuration files first to optimize Docker layer caching
COPY pyproject.toml ./

# Install dependencies directly into the system environment
RUN uv sync

# Copy your server script
COPY server.py .

# Expose the HTTP port FastMCP will run on
EXPOSE 8000

# Force Python output to be unbuffered so logs appear instantly
ENV PYTHONUNBUFFERED=1

# Run FastMCP via the system context using its built-in HTTP server CLI wrapper
CMD ["uv", "run", "server.py"]