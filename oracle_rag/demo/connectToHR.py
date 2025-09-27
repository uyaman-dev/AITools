import oracledb
import sys
# HR kullanıcısı ile bağlanıyoruz
dsn = "localhost:1521/XE"
user = "hr"
password = "hrpass" # Script'e girerken belirlediğiniz şifre

try:
    with oracledb.connect(user=user, password=password, dsn=dsn) as connection:
        print("Oracle HR şemasına başarıyla bağlanıldı! Kullanıcı artık mevcut.")
        cursor = connection.cursor()
        cursor.execute("SELECT count(*) FROM employees")
        count = cursor.fetchone()[0]
        print(f"Employees tablosunda {count} adet kayıt bulundu.")

except oracledb.Error as e:
    print("Bağlantı hatası:", e)
    sys.exit(1)