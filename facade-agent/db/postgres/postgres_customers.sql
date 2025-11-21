CREATE TABLE customers (
    customerid SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT NOT NULL
);

INSERT INTO customers (name, email, phone, address) VALUES
('Acme Corp', 'contact@acmecorp.com', '555-1001', '100 Acme Way, New York, NY'),
('Beta LLC', 'info@betallc.com', '555-1002', '200 Beta Blvd, Los Angeles, CA'),
('Gamma Inc', 'hello@gammainc.com', '555-1003', '300 Gamma Rd, Chicago, IL'),
('Delta Co', 'support@deltaco.com', '555-1004', '400 Delta Ave, Houston, TX'),
('Epsilon Ltd', 'contact@epsilonltd.com', '555-1005', '500 Epsilon St, Phoenix, AZ'),
('Zeta Group', 'info@zetagroup.com', '555-1006', '600 Zeta Ln, Philadelphia, PA'),
('Eta Partners', 'hello@etapartners.com', '555-1007', '700 Eta Dr, San Antonio, TX'),
('Theta Solutions', 'support@thetasolutions.com', '555-1008', '800 Theta Ct, San Diego, CA'),
('Iota Services', 'contact@iotaservices.com', '555-1009', '900 Iota Pl, Dallas, TX'),
('Kappa Enterprises', 'info@kappaenterprises.com', '555-1010', '1000 Kappa Cir, San Jose, CA');
