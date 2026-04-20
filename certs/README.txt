将你的证书文件放到此目录：
  cert.pem  —— TLS 证书（含完整证书链）
  key.pem   —— 私钥

打包时这两个文件会自动嵌入可执行文件中。

如需生成自签证书（仅用于测试）：
  openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout key.pem -out cert.pem \
    -days 3650 -subj "/CN=client-info-service"
