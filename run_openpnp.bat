@echo off
REM Launch OpenPnP from build directory with Java 17 compatibility
cd /d "%~dp0openpnp"
java --add-opens=java.base/java.lang=ALL-UNNAMED --add-opens=java.desktop/java.awt=ALL-UNNAMED --add-opens=java.desktop/java.awt.color=ALL-UNNAMED -jar target\openpnp-gui-0.0.1-alpha-SNAPSHOT.jar
