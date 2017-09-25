/*
 * appenlib.sql
 *
 * version 0.1
 * history
 *   0.1   initial version for review
 */

DROP TABLE document_type;
CREATE TABLE document_type (
  id serial NOT NULL, 
  doc_type text NOT NULL, 
  PRIMARY KEY (doc_type), 
  CONSTRAINT non_empty_doc_type CHECK(btrim(doc_type, ' ') != '') 
);
insert into document_type (doc_type) values ('Misc');
insert into document_type (doc_type) values ('Process');
insert into document_type (doc_type) values ('Data');

DROP SEQUENCE document_id_seq;
CREATE SEQUENCE document_id_seq INCREMENT 1
  MINVALUE 1 MAXVALUE 2147483647 START 1 CACHE 1;

DROP TABLE doc_inventory;
CREATE TABLE doc_inventory (
  doc_id integer DEFAULT nextval('document_id_seq'::text) NOT NULL, 
  doc_type text NOT NULL, 
  PRIMARY KEY (doc_id)
);

DROP TABLE doc_list;
CREATE TABLE doc_list (
  doc_id    integer NOT NULL,   --unique doc id
  version   integer[] NOT NULL, --major.minor.update
  baselined boolean NOT NULL DEFAULT FALSE, --no update if TRUE
  eformid   integer,            --required if baselined is TRUE
  title     text NOT NULL,      --each version can have its own title
  author    text[] NOT NULL,    --may have multiple authors
  keyword   text[] NOT NULL,    --may have multiple keywords
  memo      text,               --optional description
  doc_obj   OID NOT NULL,       --refers to real file
  mtime     timestamp with time zone NOT NULL DEFAULT "now"(), 
  muser     text NOT NULL DEFAULT "current_user"(), 
  PRIMARY KEY (doc_id, version)
);

DROP INDEX idx_doc_list_doc_id;
CREATE INDEX idx_doc_list_doc_id ON doc_list (doc_id);

DROP INDEX idx_doc_list_doc_id_ver;
CREATE INDEX idx_doc_list_doc_id_ver ON doc_list (doc_id, version);

DROP FUNCTION create_doc(text, integer[], text, text[], text[], text, text);
CREATE OR REPLACE FUNCTION create_doc(text, integer[], text, text[], 
text[], text, text) RETURNS integer AS '
  --creates new document entry in library and returns document id
  --parameter list: doctype, version, title, author, keyword, memo, path
  --return values: doc_id if success, negative values on errors
  DECLARE
    docid   integer;
    tmpoid  integer;
    tmp     text;
    doctype text;
    ver     integer[];
    foid    integer;
  BEGIN
    --check input arguments
    --doctype is mandatory
    tmp := CASE WHEN $1 IS NULL THEN '''' ELSE btrim($1, '' '') END;
    IF tmp = '''' THEN RETURN -1; END IF;
    --default version: 0.1
    IF $2 IS NULL THEN ver := ARRAY[0,1]; ELSE ver := $2; END IF;
    --title, author, keyword, path are mandatory
    IF $3 IS NULL THEN RETURN -3; END IF;
    IF $4 IS NULL THEN RETURN -4; END IF;
    IF $5 IS NULL THEN RETURN -5; END IF;
    IF $7 IS NULL THEN RETURN -7; END IF;
    --import file, exit on error
    foid := lo_import($7);
    --add doctype if neccessary
    SELECT INTO doctype doc_type FROM document_type
     WHERE lower(doc_type)=lower(tmp);
    IF NOT FOUND THEN
      INSERT INTO document_type (doc_type) VALUES (tmp);
      doctype := tmp;
    END IF;
    --add entry in doc_inventory
    INSERT INTO doc_inventory (doc_id, doc_type) 
    VALUES (DEFAULT, doctype);
    GET DIAGNOSTICS tmpoid = RESULT_OID;
    SELECT INTO docid doc_id FROM doc_inventory WHERE OID=tmpoid;
    --add entry in doc_list
    INSERT INTO doc_list (doc_id, version, title, author, keyword, 
    memo, doc_obj) VALUES (docid, ver, $3, $4, $5, $6, foid);
    RETURN docid;
  END;
' LANGUAGE 'plpgsql';

DROP FUNCTION delete_doc_ver(integer, integer[]);
CREATE OR REPLACE FUNCTION delete_doc_ver(integer, integer[]) 
RETURNS integer AS '
  --delete document from library
  --parameter list: doc_id, version
  --return values: 1 on success, 0 if no version left, -1 on error
  DECLARE
    foid   integer;
    result integer;
  BEGIN
    SELECT INTO foid doc_obj FROM doc_list 
     WHERE doc_id=$1 AND version=$2;
    IF NOT FOUND THEN RETURN -1; END IF;
    result := lo_unlink(foid);
    DELETE FROM doc_list WHERE doc_id=$1 AND version=$2;
    SELECT INTO result COUNT(*) FROM doc_list WHERE doc_id=$1;
    IF result > 0 THEN RETURN 1; END IF;
    --no other version left, delete inventory entry
    DELETE FROM doc_inventory WHERE doc_id=$1;
    RETURN 0;
  END;
' LANGUAGE 'plpgsql';

DROP FUNCTION baseline_doc(integer, integer[], integer);
CREATE OR REPLACE FUNCTION baseline_doc(integer, integer[], integer) 
RETURNS integer AS '
  --baseline document in library
  --parameter list: doc_id, version, eformid
  --return values: 1 if success, 0 if no update needed, -1 on errors
  DECLARE
    status boolean;
    oeform integer;
    equal  boolean;
  BEGIN
    IF $1 IS NULL OR $2 IS NULL OR $3 IS NULL THEN RETURN -1; END IF;
    SELECT INTO status, oeform baselined, eformid FROM doc_list
     WHERE doc_id=$1 AND version=$2;
    IF NOT FOUND THEN RETURN -1; END IF;
    IF status THEN
      equal := CASE WHEN oeform IS NOT NULL THEN oeform=$3 
                    ELSE FALSE END;
      IF equal THEN RETURN 0; END IF;
    END IF;
    UPDATE doc_list SET baselined=TRUE, eformid=$3
     WHERE doc_id=$1 AND version=$2;
    RETURN 1;
  END;
' LANGUAGE 'plpgsql';

DROP FUNCTION get_latest_ver(integer);
CREATE OR REPLACE FUNCTION get_latest_ver(integer) RETURNS integer[] AS '
  DECLARE
    result integer[];
  BEGIN
    SELECT INTO result version FROM doc_list 
     WHERE doc_id=$1 ORDER BY version DESC LIMIT 1;
    IF NOT FOUND THEN RETURN NULL; END IF;
    RETURN result;
  END;
' LANGUAGE 'plpgsql';

DROP FUNCTION update_doc(integer, integer[], text, text[], text[], text, text);
CREATE OR REPLACE FUNCTION update_doc(integer, integer[], text, 
text[], text[], text, text) RETURNS integer AS '
  --update document entry
  --parameter list: doc_id, version, title, author, keyword, memo, path
  --return values: 1 on success, -1 on error
  DECLARE
    otitle  text;
    oauthor text[];
    okw     text[];
    omemo   text;
    foid    integer;
    noid    integer;
    status  boolean;
  BEGIN
    SELECT INTO status, otitle, oauthor, okw, omemo, foid 
                baselined, title, author, keyword, memo, doc_obj 
      FROM doc_list 
     WHERE doc_id=$1 AND version=$2;
    IF NOT FOUND THEN RETURN -1; END IF;
    IF status THEN RETURN -1; END IF;
    IF $3 IS NOT NULL THEN otitle := $3; END IF;
    IF $4 IS NOT NULL THEN oauthor := $4; END IF;
    IF $5 IS NOT NULL THEN okw := $5; END IF;
    IF $6 IS NOT NULL THEN omemo := $6; END IF;
    IF $7 IS NOT NULL THEN
      noid := lo_import($7);
      SELECT lo_unlink(foid);
    ELSE
      noid := foid;
    END IF;
    UPDATE doc_list SET title=otitle, author=oauthor, keyword=okw, 
      memo=omemo, doc_obj=noid, mtime=DEFAULT, muser=DEFAULT;
    RETURN 1;
  END;
' LANGUAGE 'plpgsql';

DROP FUNCTION search_by_keyword(text);
CREATE OR REPLACE FUNCTION search_by_keyword(text)
RETURNS SETOF doc_list AS '
  DECLARE
    tmp doc_list;
  BEGIN
    IF $1 IS NULL THEN RETURN; END IF;
    FOR tmp IN SELECT * FROM doc_list 
        WHERE lower($1) = ANY (lower_array(keyword)) LOOP
      RETURN NEXT tmp;
    END LOOP;
    RETURN;
  END;
' LANGUAGE 'plpgsql';

DROP FUNCTION search_by_keywords(text[]);
CREATE OR REPLACE FUNCTION search_by_keywords(text[]) 
RETURNS SETOF doc_list AS '
  DECLARE
    tmp doc_list;
    cmd text;
    i   int;
  BEGIN
    IF $1 IS NULL THEN RETURN; END IF;
    cmd := ''SELECT * FROM doc_list WHERE ('';
    FOR i IN array_lower($1, 1) .. array_upper($1, 1) LOOP
      cmd := cmd || quote_literal(lower($1[i])) || 
        '' = ANY (lower_array(keyword)) OR '';
    END LOOP;
    cmd := rtrim(cmd, '' OR'') || '')'';
    --RAISE INFO ''%'', cmd;
    FOR tmp IN EXECUTE cmd LOOP
      RETURN NEXT tmp;
    END LOOP;
    RETURN;
  END;
' LANGUAGE 'plpgsql';

DROP FUNCTION lower_array(text[]);
CREATE OR REPLACE FUNCTION lower_array(text[]) RETURNS text[] AS '
  DECLARE
    i      integer;
    result text[];
  BEGIN
    IF $1 IS NULL THEN RETURN NULL; END IF;
    result := $1;
    FOR i IN array_lower($1, 1) .. array_upper($1, 1) LOOP
      result[i] := lower($1[i]);
    END LOOP;
    RETURN result;
  END;
' LANGUAGE 'plpgsql';

DROP FUNCTION add_new_ver(integer, integer[], text, text[], text[], text, text);
CREATE OR REPLACE FUNCTION add_new_ver(integer, integer[], text, 
text[], text[], text, text) RETURNS integer AS '
  --add new document version
  --parameter list: doc_id, version, title, author, keyword, memo, path
  --return values: 1 if success, -1 on error
  DECLARE
    path    text;
    over    integer[];
    otitle  text;
    oauthor text[];
    okw     text[];
    omemo   text;
  BEGIN
    IF $1 IS NULL OR $2 IS NULL OR $7 IS NULL THEN RETURN -1; END IF;
    path := btrim($7, '' '');
    IF path = '''' THEN RETURN -1; END IF;
    SELECT INTO over, otitle, oauthor, okw, omemo 
                version, title, author, keyword, memo
      FROM doc_list WHERE doc_id=$1 ORDER BY version DESC LIMIT 1;
    IF NOT FOUND THEN RETURN -1; END IF;
    IF NOT $2 > over THEN RETURN -1; END IF;
    IF $3 IS NOT NULL THEN otitle := $3; END IF;
    IF $4 IS NOT NULL THEN oauthor := $4; END IF;
    IF $5 IS NOT NULL THEN okw := $5; END IF;
    IF $6 IS NOT NULL THEN omemo := $6; END IF;
    INSERT INTO doc_list (doc_id, version, title, author, keyword, 
        memo, doc_obj) VALUES ($1, $2, otitle, oauthor, okw, omemo, 
        lo_import($7));
    RETURN 1;
  END;
' LANGUAGE 'plpgsql';

DROP FUNCTION get_doc_copy(integer, integer[]);
CREATE OR REPLACE FUNCTION get_doc_copy(integer, integer[], text) 
RETURNS integer AS '
  --save a copy of designated document version
  --parameter list: doc_id, version, path
  --return values: 1 if success, -1 on error
  DECLARE
    foid integer;
  BEGIN
    IF $2 IS NULL THEN
      SELECT INTO foid doc_obj FROM doc_list 
       WHERE doc_id=$1 ORDER BY version DESC LIMIT 1;
    ELSE
      SELECT INTO foid doc_obj FROM doc_list
       WHERE doc_id=$1 AND version=$2;
    END IF;
    IF NOT FOUND THEN RETURN -1; END IF;
    PERFORM lo_export(foid, $3);
    RETURN 1;
  END;
' LANGUAGE 'plpgsql';

