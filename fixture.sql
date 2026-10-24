CREATE TABLE orders(id INTEGER PRIMARY KEY, product TEXT NOT NULL, status TEXT NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0));
INSERT INTO orders VALUES (1,'Demo Notebook','paid',1200),(2,'Demo Pen','paid',300),(3,'Demo Notebook','pending',1200),(4,'Demo Notebook','paid',1200),(5,'Demo Pen','cancelled',300);
CREATE TABLE private_notes(note TEXT);
INSERT INTO private_notes VALUES ('synthetic secret used to test table denial');
