CREATE TABLE users (
  id INT PRIMARY KEY AUTO_INCREMENT,
  userid VARCHAR(50) NOT NULL,
  amount VARCHAR(100) NOT NULL
);

INSERT INTO users (userid, amount) VALUES ('pong', '10');
INSERT INTO users (userid, amount) VALUES ('naro', '50.0');
INSERT INTO users (userid, amount) VALUES ('det123', '67.6');
INSERT INTO users (userid, amount) VALUES ('nee12', '56.0');
INSERT INTO users (userid, amount) VALUES ('ro22', '45.0');
INSERT INTO users (userid, amount) VALUES ('jaekeo', '23.3');

