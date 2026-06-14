// MongoDB 初始化脚本：创建 ginkgo 用户（readWrite，quant 库），供 Docker 实例首启执行
db.createUser(
    {
        user: "ginkgo",
        pwd: "needtryharder",
        roles: [
            {
                role: "readWrite",
                db: "quant"
            }
        ]
    }
);
