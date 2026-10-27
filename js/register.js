const REGISTER_URL = 'http://localhost:3000/auth/register';

document.addEventListener('DOMContentLoaded', () => {
    const registerForm = document.querySelector('.register-form');

    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Збираємо дані
            const fullName = document.getElementById('reg-name').value;
            const email = document.getElementById('reg-email').value;
            const password = document.getElementById('reg-pass').value;
            
            // 1. Читаємо вибрану роль з випадаючого списку
            const roleSelect = document.getElementById('reg-role');
            const selectedRole = roleSelect ? roleSelect.value : 'User'; // Якщо списку немає, то за замовчуванням User

            // (Опціонально) Перевірка паролів, якщо є поле підтвердження
            const confirmPassInput = document.getElementById('reg-pass-confirm');
            if (confirmPassInput && password !== confirmPassInput.value) {
                alert('Паролі не співпадають!');
                return;
            }

            try {
                const response = await fetch(REGISTER_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        fullName, 
                        email, 
                        password,
                        role: selectedRole // 
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    alert(`Успішно! Ви зареєстровані як ${selectedRole === 'Admin' ? 'Адміністратор' : 'Покупець'}.`);
                    window.location.href = 'login.html';
                } else {
                    alert('Помилка: ' + data.message);
                }
            } catch (error) {
                console.error(error);
                alert('Сервер не відповідає');
            }
        });
    }
});