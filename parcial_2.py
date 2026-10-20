import sqlite3
from datetime import datetime

DB = "inventario.db"


def conectar():
    conexion = sqlite3.connect(DB)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def crear_tablas():
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL CHECK(precio >= 0),
                cantidad INTEGER NOT NULL CHECK(cantidad >= 0)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER NOT NULL,
                cantidad INTEGER NOT NULL CHECK(cantidad > 0),
                precio_unitario REAL NOT NULL CHECK(precio_unitario >= 0),
                fecha TEXT NOT NULL,
                FOREIGN KEY (producto_id)
                    REFERENCES productos(id)
                    ON DELETE RESTRICT
            )
        """)


def registrar_producto():
    try:
        nombre = input("Nombre del producto: ").strip()

        if not nombre:
            print("El nombre no puede estar vacio.")
            return

        precio = float(input("Precio del producto: "))
        cantidad = int(input("Cantidad disponible: "))

        if precio < 0 or cantidad < 0:
            print("El precio y la cantidad no pueden ser negativos.")
            return

        with conectar() as con:
            con.execute("""
                INSERT INTO productos (nombre, precio, cantidad)
                VALUES (?, ?, ?)
            """, (nombre, precio, cantidad))

        print(" El producto ha sido registrado correctamente.")

    except ValueError:
        print("Ingresa valores numericos validos.")
    except sqlite3.Error as e:
        print("Error de base de datos:", e)


def consultar_productos():
    try:
        con = conectar()
        cursor = con.cursor()

        cursor.execute("""
            SELECT id, nombre, precio, cantidad
            FROM productos
            ORDER BY id
        """)

        productos = cursor.fetchall()
        con.close()

        print("\n--- INVENTARIO DE PRODUCTOS ---")

        if len(productos) == 0:
            print("No hay productos registrados.")
            return

        for id_producto, nombre, precio, cantidad in productos:
            print(f"ID: {id_producto}")
            print(f"Nombre: {nombre}")
            print(f"Precio: ${precio:.2f}")
            print(f"Stock: {cantidad}")
            print("-" * 30)

    except sqlite3.Error as e:
        print("Error al consultar productos:", e)

def actualizar_producto():
    try:
        producto_id = int(input("ID del producto: "))

        print("1. Actualizar precio")
        print("2. Actualizar cantidad")

        opcion = input("Selecciona una opcion: ")

        if opcion == "1":
            campo = "precio"
            valor = float(input("Nuevo precio: "))

        elif opcion == "2":
            campo = "cantidad"
            valor = int(input("Nueva cantidad: "))

        else:
            print("Opcion invalida.")
            return

        if valor < 0:
            print("El valor no puede ser negativo.")
            return

        consultas = {
            "precio": "UPDATE productos SET precio = ? WHERE id = ?",
            "cantidad": "UPDATE productos SET cantidad = ? WHERE id = ?"
        }

        with conectar() as con:
            resultado = con.execute(
                consultas[campo],
                (valor, producto_id)
            )

            if resultado.rowcount == 0:
                print("Producto no encontrado.")
            else:
                print("Producto actualizado correctamente.")

    except ValueError:
        print("Ingresa valores validos.")
    except sqlite3.Error as e:
        print("Error de base de datos:", e)


def eliminar_producto():
    try:
        producto_id = int(input("ID del producto que deseas eliminar: "))

        with conectar() as con:
            resultado = con.execute(
                "DELETE FROM productos WHERE id = ?",
                (producto_id,)
            )

            if resultado.rowcount == 0:
                print("Producto no encontrado.")
            else:
                print("Producto eliminado correctamente.")

    except ValueError:
        print("El ID debe ser un numero entero.")
    except sqlite3.IntegrityError:
        print("No se puede eliminar porque tiene ventas registradas.")
    except sqlite3.Error as e:
        print("Error de base de datos:", e)


def registrar_venta(probar_error=False):
    con = conectar()

    try:
        producto_id = int(input("ID del producto: "))
        cantidad = int(input("Cantidad que deseas vender: "))

        if cantidad <= 0:
            print("La cantidad debe ser mayor que cero.")
            return

        con.execute("BEGIN")

        producto = con.execute("""
            SELECT nombre, precio, cantidad
            FROM productos
            WHERE id = ?
        """, (producto_id,)).fetchone()

        if producto is None:
            raise ValueError("El producto no existe.")

        nombre, precio, stock = producto

        if stock < cantidad:
            raise ValueError(
                f"Inventario insuficiente. Stock disponible: {stock}"
            )

        con.execute("""
            INSERT INTO ventas
                (producto_id, cantidad, precio_unitario, fecha)
            VALUES (?, ?, ?, ?)
        """, (
            producto_id,
            cantidad,
            precio,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        if probar_error:
            raise RuntimeError("Error controlado de prueba.")

        resultado = con.execute("""
            UPDATE productos
            SET cantidad = cantidad - ?
            WHERE id = ? AND cantidad >= ?
        """, (cantidad, producto_id, cantidad))

        if resultado.rowcount != 1:
            raise RuntimeError("No se pudo actualizar el inventario.")

        con.commit()

        print("\nVenta registrada correctamente.")
        print("Producto:", nombre)
        print("Cantidad vendida:", cantidad)
        print(f"Precio unitario: ${precio:.2f}")
        print(f"Total de la venta: ${precio * cantidad:.2f}")

    except (ValueError, RuntimeError) as e:
        con.rollback()
        print("Venta cancelada:", e)
        print("Se revirtieron los cambios de la transaccion.")

    except sqlite3.Error as e:
        con.rollback()
        print("Error de base de datos:", e)
        print("Se revirtieron los cambios de la transaccion.")

    finally:
        con.close()


def historial_ventas():
    try:
        with conectar() as con:
            ventas = con.execute("""
                SELECT
                    v.id,
                    p.nombre,
                    v.cantidad,
                    v.precio_unitario,
                    v.cantidad * v.precio_unitario AS total,
                    v.fecha
                FROM ventas AS v
                INNER JOIN productos AS p
                    ON v.producto_id = p.id
                ORDER BY v.id DESC
            """).fetchall()

        print("\n--- HISTORIAL DE VENTAS ---")

        if not ventas:
            print("No hay ventas registradas.")
            return

        for v in ventas:
            print(
                f"Venta #{v[0]} | Producto: {v[1]} | "
                f"Cantidad: {v[2]} | "
                f"Precio unitario: ${v[3]:.2f} | "
                f"Total: ${v[4]:.2f} | Fecha: {v[5]}"
            )

    except sqlite3.Error as e:
        print("Error de base de datos:", e)


def probar_rollback():
    try:
        producto_id = int(
            input("ID del producto para probar rollback: ")
        )

        cantidad = int(
            input("Cantidad que se intentara vender: ")
        )

        if cantidad <= 0:
            print("La cantidad debe ser mayor que cero.")
            return

        with conectar() as con:
            inventario_antes = con.execute("""
                SELECT id, cantidad
                FROM productos
                ORDER BY id
            """).fetchall()

            ventas_antes = con.execute(
                "SELECT COUNT(*) FROM ventas"
            ).fetchone()[0]

            existe = con.execute(
                "SELECT id FROM productos WHERE id = ?",
                (producto_id,)
            ).fetchone()

        if existe is None:
            print("El producto no existe.")
            return

        print("\n--- ESTADO ANTES DE LA PRUEBA ---")
        print("Inventario:", inventario_antes)
        print("Cantidad de ventas:", ventas_antes)

        registrar_venta(probar_error=True)

        with conectar() as con:
            inventario_despues = con.execute("""
                SELECT id, cantidad
                FROM productos
                ORDER BY id
            """).fetchall()

            ventas_despues = con.execute(
                "SELECT COUNT(*) FROM ventas"
            ).fetchone()[0]

        print("\n--- ESTADO DESPUES DE LA PRUEBA ---")
        print("Inventario:", inventario_despues)
        print("Cantidad de ventas:", ventas_despues)

        if (
            inventario_antes == inventario_despues
            and ventas_antes == ventas_despues
        ):
            print("\nPRUEBA SUPERADA.")
            print("Rollback cancelo la operacion completa.")
            print("Los datos permanecieron intactos.")
        else:
            print("\nPRUEBA FALLIDA.")
            print("Se detectaron cambios inesperados.")

    except ValueError:
        print("Debes ingresar numeros validos.")
    except sqlite3.Error as e:
        print("Error durante la prueba:", e)


def menu():
    crear_tablas()

    while True:
        print("\n======================================")
        print(" SISTEMA DE INVENTARIO Y VENTAS")
        print("======================================")
        print("1. Registrar producto")
        print("2. Consultar productos")
        print("3. Actualizar producto")
        print("4. Eliminar producto")
        print("5. Registrar venta")
        print("6. Consultar historial de ventas")
        print("7. Probar rollback")
        print("0. Salir")

        opcion = input("Selecciona una opcion: ").strip()

        if opcion == "1":
            registrar_producto()
        elif opcion == "2":
            consultar_productos()
        elif opcion == "3":
            actualizar_producto()
        elif opcion == "4":
            eliminar_producto()
        elif opcion == "5":
            registrar_venta()
        elif opcion == "6":
            historial_ventas()
        elif opcion == "7":
            probar_rollback()
        elif opcion == "0":
            print("Programa finalizado.")
            break
        else:
            print("Opcion invalida. Intente nuevamente.")


if __name__ == "__main__":
    menu()