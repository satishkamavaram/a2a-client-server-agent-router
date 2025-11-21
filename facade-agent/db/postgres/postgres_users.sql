CREATE TABLE users (
    userid SERIAL PRIMARY KEY,
    firstname TEXT NOT NULL,
    lastname TEXT NOT NULL,
    emailid TEXT NOT NULL,
    gender TEXT NOT NULL
);

INSERT INTO users (firstname, lastname, emailid, gender) VALUES
('Alice', 'Smith', 'alice.smith@example.com', 'Female'),
('Bob', 'Johnson', 'bob.johnson@example.com', 'Male'),
('Carol', 'Williams', 'carol.williams@example.com', 'Female'),
('David', 'Brown', 'david.brown@example.com', 'Male'),
('Eve', 'Jones', 'eve.jones@example.com', 'Female'),
('Frank', 'Garcia', 'frank.garcia@example.com', 'Male'),
('Grace', 'Martinez', 'grace.martinez@example.com', 'Female'),
('Henry', 'Rodriguez', 'henry.rodriguez@example.com', 'Male'),
('Ivy', 'Lee', 'ivy.lee@example.com', 'Female'),
('Jack', 'Walker', 'jack.walker@example.com', 'Male');
