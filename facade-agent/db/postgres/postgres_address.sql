CREATE TABLE address (
    addressid SERIAL PRIMARY KEY,
    userid INT REFERENCES users(userid),
    street TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    zip TEXT NOT NULL,
    country TEXT NOT NULL
);

INSERT INTO address (userid, street, city, state, zip, country) VALUES
(1, '123 Main St', 'New York', 'NY', '10001', 'USA'),
(2, '456 Oak Ave', 'Los Angeles', 'CA', '90001', 'USA'),
(3, '789 Pine Rd', 'Chicago', 'IL', '60601', 'USA'),
(4, '321 Maple Dr', 'Houston', 'TX', '77001', 'USA'),
(5, '654 Cedar Ln', 'Phoenix', 'AZ', '85001', 'USA'),
(6, '987 Birch Blvd', 'Philadelphia', 'PA', '19101', 'USA'),
(7, '246 Spruce St', 'San Antonio', 'TX', '78201', 'USA'),
(8, '135 Elm St', 'San Diego', 'CA', '92101', 'USA'),
(9, '864 Willow Ave', 'Dallas', 'TX', '75201', 'USA'),
(10, '579 Aspen Ct', 'San Jose', 'CA', '95101', 'USA');
