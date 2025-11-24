-- public.customers definition

-- Drop table

-- DROP TABLE public.customers;

CREATE TABLE public.customers (
	customerid serial4 NOT NULL,
	"name" text NOT NULL,
	email text NOT NULL,
	phone text NOT NULL,
	address text NOT NULL,
	CONSTRAINT customers_pkey PRIMARY KEY (customerid)
);


-- public.users definition

-- Drop table

-- DROP TABLE public.users;

CREATE TABLE public.users (
	userid serial4 NOT NULL,
	firstname text NOT NULL,
	lastname text NOT NULL,
	emailid text NOT NULL,
	gender text NOT NULL,
	CONSTRAINT users_pkey PRIMARY KEY (userid)
);


-- public.address definition

-- Drop table

-- DROP TABLE public.address;

CREATE TABLE public.address (
	addressid serial4 NOT NULL,
	userid int4 NULL,
	street text NOT NULL,
	city text NOT NULL,
	state text NOT NULL,
	zip text NOT NULL,
	country text NOT NULL,
	CONSTRAINT address_pkey PRIMARY KEY (addressid),
	CONSTRAINT address_userid_fkey FOREIGN KEY (userid) REFERENCES public.users(userid)
);


-- public.sales definition

-- Drop table

-- DROP TABLE public.sales;

CREATE TABLE public.sales (
	saleid serial4 NOT NULL,
	userid int4 NULL,
	customerid int4 NULL,
	"date" date NOT NULL,
	amount numeric NOT NULL,
	CONSTRAINT sales_pkey PRIMARY KEY (saleid),
	CONSTRAINT sales_customerid_fkey FOREIGN KEY (customerid) REFERENCES public.customers(customerid),
	CONSTRAINT sales_userid_fkey FOREIGN KEY (userid) REFERENCES public.users(userid)
);