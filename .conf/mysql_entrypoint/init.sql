mysql -uroot -proot
CREATE DATABASE 'ginkgo' default character set utf8 collate utf8_general_ci;
REVOKE ALL PRIVILEGES ON *.* FROM 'ginkgoadm'@'%';
GRANT ALL PRIVILEGES ON ginkgo.* TO 'ginkgoadm'@'%';
FLUSH PRIVILEGES;
