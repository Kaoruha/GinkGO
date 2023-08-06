mysql -uroot -proot
CREATE DATABASE 'ginkgo' default character set utf8 collate utf8_general_ci;
GRANT ALL ON *.* TO 'ginkgoadm'@'%' IDENTIFIED BY 'hellomysql' WITH GRANT OPTION;
FLUSH PRIVILEGES;
