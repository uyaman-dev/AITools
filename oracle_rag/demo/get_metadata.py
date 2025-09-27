import oracledb
import sys
from tabulate import tabulate

def get_hr_metadata(connection):
    try:
        cursor = connection.cursor()

        # Tüm tabloları listele
        print("\n=== HR Şemasındaki Tablolar ===")
        cursor.execute("""
            SELECT t.table_name, 
                   NVL(TO_CHAR(t.num_rows), 'N/A'), 
                   NVL(t.tablespace_name, 'N/A'), 
                   NVL(TO_CHAR(t.last_analyzed, 'DD-MM-YYYY HH24:MI:SS'), 'Analiz yok'),
                   NVL(tc.comments, 'Açıklama yok') as table_comment
            FROM all_tables t
            LEFT JOIN all_tab_comments tc ON t.owner = tc.owner 
                AND t.table_name = tc.table_name
            WHERE t.owner = 'HR'
            ORDER BY t.table_name
        """)
        tables = cursor.fetchall()
        print(tabulate(tables,
                       headers=['Tablo Adı', 'Kayıt Sayısı', 'Tablespace',
                                'Son Analiz Tarihi', 'Tablo Açıklaması'],
                       tablefmt='grid',
                       maxcolwidths=[None, None, None, None, 50]))

        # Her tablo için sütun bilgilerini al
        print("\n=== Tablo Sütunları ===")
        for table in tables:
            table_name = table[0]
            table_comment = table[4]

            print(f"\n{'-'*80}")
            print(f"Tablo: {table_name}")
            print(f"Açıklama: {table_comment}")
            print(f"{'-'*80}")

            cursor.execute("""
                SELECT 
                    c.column_name, 
                    c.data_type || 
                        CASE 
                            WHEN c.data_type IN ('VARCHAR2', 'CHAR', 'VARCHAR') THEN 
                                '(' || c.char_length || ' ' || 
                                CASE WHEN c.char_used = 'B' THEN 'BYTE' ELSE 'CHAR' END || ')'
                            WHEN c.data_type = 'NUMBER' AND c.data_precision IS NOT NULL THEN 
                                '(' || c.data_precision || 
                                CASE WHEN c.data_scale > 0 THEN ',' || c.data_scale ELSE '' END || ')'
                            ELSE ''
                        END as data_type,
                    c.nullable,
                    c.data_default,
                    NVL(cc.comments, 'Açıklama yok') as column_comment
                FROM all_tab_columns c
                LEFT JOIN all_col_comments cc ON c.owner = cc.owner 
                    AND c.table_name = cc.table_name 
                    AND c.column_name = cc.column_name
                WHERE c.owner = 'HR' 
                    AND c.table_name = :table_name
                ORDER BY c.column_id
            """, table_name=table_name)

            columns = cursor.fetchall()
            if columns:
                print("\nSütunlar:")
                # None değerleri boş string ile değiştir
                formatted_columns = [
                    ['' if col is None else col for col in row]
                    for row in columns
                ]
                print(tabulate(
                    formatted_columns,
                    headers=['Sütun Adı', 'Veri Tipi', 'Null İzni',
                             'Varsayılan Değer', 'Açıklama'],
                    tablefmt='grid',
                    maxcolwidths=[None, None, None, 20, 40]
                ))

            # Primary Key bilgileri
            cursor.execute("""
                SELECT cols.column_name
                FROM all_constraints cons, all_cons_columns cols
                WHERE cons.owner = 'HR'
                AND cons.table_name = :table_name
                AND cons.constraint_type = 'P'
                AND cons.constraint_name = cols.constraint_name
                AND cons.owner = cols.owner
            """, table_name=table_name)

            pks = [row[0] for row in cursor.fetchall()]
            if pks:
                print(f"\nPrimary Key: {', '.join(pks)}")

            # Foreign Key bilgileri
            cursor.execute("""
                SELECT a.column_name, 
                       c_pk.table_name as references_table,
                       c_pk.constraint_name as fk_name
                FROM all_cons_columns a
                JOIN all_constraints c ON a.owner = c.owner
                    AND a.constraint_name = c.constraint_name
                JOIN all_constraints c_pk ON c.r_owner = c_pk.owner
                    AND c.r_constraint_name = c_pk.constraint_name
                WHERE c.constraint_type = 'R'
                AND a.table_name = :table_name
                AND a.owner = 'HR'
            """, table_name=table_name)

            fks = cursor.fetchall()
            if fks:
                print("\nForeign Keys:")
                for fk in fks:
                    print(f"  {fk[0]} -> {fk[1]}.{fk[2]}")

            print(f"{'-'*80}\n")

    except oracledb.Error as e:
        print("Hata oluştu:", e)

# Ana bağlantı ve çalıştırma
dsn = "localhost:1521/XE"
user = "hr"
password = "hrpass"

try:
    with oracledb.connect(user=user, password=password, dsn=dsn) as connection:
        print("Oracle HR şemasına başarıyla bağlanıldı!")
        get_hr_metadata(connection)

except oracledb.Error as e:
    print("Bağlantı hatası:", e)
    sys.exit(1)