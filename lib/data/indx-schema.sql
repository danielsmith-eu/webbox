--    Copyright (C) 2011-2013 University of Southampton
--    Copyright (C) 2011-2013 Daniel Alexander Smith
--    Copyright (C) 2011-2013 Max Van Kleek
--    Copyright (C) 2011-2013 Nigel R. Shadbolt
--
--    This program is free software: you can redistribute it and/or modify
--    it under the terms of the GNU Affero General Public License, version 3,
--    as published by the Free Software Foundation.
--
--    This program is distributed in the hope that it will be useful,
--    but WITHOUT ANY WARRANTY; without even the implied warranty of
--    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
--    GNU Affero General Public License for more details.
--
--    You should have received a copy of the GNU Affero General Public License
--    along with this program.  If not, see <http://www.gnu.org/licenses/>.

CREATE TYPE uname_type AS ENUM ('local_owner', 'local', 'openid');

CREATE TABLE tbl_users
(
  id_user serial NOT NULL,
  username text NOT NULL,
  username_type uname_type NOT NULL,
  password_hash character varying(128) NOT NULL,
  password_encrypted text NOT NULL,
  CONSTRAINT pk_id_user PRIMARY KEY (id_user),
  CONSTRAINT u_username UNIQUE (username)
)
WITH (
  OIDS=FALSE
);

CREATE TYPE db_user_typ AS ENUM ('rw', 'ro');

CREATE TABLE tbl_keychain
(
  id_key serial NOT NULL,
  user_id integer NOT NULL,
  db_name character varying(64) NOT NULL,
  db_user character varying(64) NOT NULL,
  db_user_type db_user_typ NOT NULL,
  db_password_encrypted text NOT NULL,
  CONSTRAINT pk_id_key PRIMARY KEY (id_key),
  CONSTRAINT fk_user_id FOREIGN KEY (user_id)
      REFERENCES tbl_users (id_user) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION
)
WITH (
    OIDS=FALSE
);

