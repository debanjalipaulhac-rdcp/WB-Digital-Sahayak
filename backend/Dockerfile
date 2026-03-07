FROM public.ecr.aws/lambda/python:3.13

# ✅ More reliable - use RPM/dnf
RUN dnf install -y tar xz ffmpeg || \
    (dnf install -y tar xz && \
     curl --retry 3 --retry-delay 5 -L \
     https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
     -o /tmp/ffmpeg.tar.xz && \
     tar -xJf /tmp/ffmpeg.tar.xz -C /tmp && \
     mv /tmp/ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg && \
     chmod +x /usr/local/bin/ffmpeg && \
     rm -rf /tmp/ffmpeg*)

# Verify
RUN ffmpeg -version

COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

COPY . .
CMD ["main.handler"]