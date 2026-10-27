const API_URL = 'http://localhost:3000/auth/login';

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.querySelector('.login-form');

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault(); 

            // 1. Збираємо дані з полів
            const email = document.getElementById('user-email').value;
            const password = document.getElementById('user-pass').value;

            try {
                // 2. Відправляємо на сервер
                const response = await fetch(API_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();

                if (response.ok) {
                    localStorage.setItem('token', data.token);
                                       
                    if (data.role === 'Admin') {
                        window.location.href = 'admin.html';
                    } else {
                        window.location.href = 'profile.html'; 
                    }
                } else {
                    
                    alert(data.message || 'Помилка входу');
                }
            } catch (error) {
                console.error('Помилка:', error);
                alert('Сервер не відповідає. Перевірте, чи запущено бекенд.');
            }
        });
    }
});