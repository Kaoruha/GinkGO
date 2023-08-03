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
