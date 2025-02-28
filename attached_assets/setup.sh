#!/bin/bash

# Set JAVA_HOME dynamically
if [ -d "/nix/store" ]; then
  # Search for Java in nix store
  JAVA_PATH=$(find /nix/store -type f -name java -path "*/bin/java" 2>/dev/null | grep -i "openjdk.*17" | head -n 1)
  if [ ! -z "$JAVA_PATH" ]; then
    export JAVA_HOME=$(dirname $(dirname $JAVA_PATH))
    export PATH=$JAVA_HOME/bin:$PATH
  else
    echo "Error: Java 17 not found in nix store"
    exit 1
  fi
else
  echo "Error: Nix store not found"
  exit 1
fi

# Debug information
echo "Current environment:"
echo "JAVA_HOME=$JAVA_HOME"
echo "PATH=$PATH"
echo "Java binary location:"
which java
echo "Java version:"
java -version
echo "Maven version:"
mvn -v || echo "Maven not found"

# Clone repository if not already cloned
if [ ! -d "Spring-PY00168" ]; then
  echo "Cloning repository..."
  git clone https://github.com/RubeeFunix/Spring-PY00168.git
  cd Spring-PY00168
else
  echo "Repository already exists, updating..."
  cd Spring-PY00168
  git pull https://github.com/RubeeFunix/Spring-PY00168.git
fi

# Run Maven build
echo "Building project with Maven..."
if [ -f "mvnw" ]; then
  chmod +x mvnw
  echo "Maven wrapper found, building project..."
  ./mvnw --version
  echo "Starting Maven build with detailed output..."
  ./mvnw clean install -DskipTests -X
else
  echo "Maven wrapper not found, downloading Maven..."
  curl -o maven.tar.gz https://dlcdn.apache.org/maven/maven-3/3.9.6/binaries/apache-maven-3.9.6-bin.tar.gz
  tar xzf maven.tar.gz
  export PATH=$PATH:$(pwd)/apache-maven-3.9.6/bin
  mvn clean install -DskipTests -X
fi

# Kiểm tra và tạo thư mục nếu chưa tồn tại
mkdir -p .replit-cache

echo "Setup completed successfully!"