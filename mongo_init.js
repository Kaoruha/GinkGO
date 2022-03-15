db.createUser(
    {
        user: "ginkgo",
        pwd: "caonima123",
        roles: [
            {
                role: "readWrite",
                db: "quant"
            }
        ]
    }
);