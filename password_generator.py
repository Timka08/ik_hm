import secrets
import string


def generate_password(length: int) -> str:
    """
    Генерирует случайный пароль заданной длины,
    состоящий из латинских букв и цифр.
    """

    if length <= 0:
        raise ValueError("Длина пароля должна быть больше 0.")

    characters = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )


def main():
    print("=== Генератор паролей ===")

    while True:
        try:
            length = int(input("Введите длину пароля: "))

            password = generate_password(length)

            print(f"\nВаш пароль: {password}")
            break

        except ValueError as error:
            print(f"Ошибка: {error}")
        except KeyboardInterrupt:
            print("\nПрограмма завершена.")
            break


if __name__ == "__main__":
    main()