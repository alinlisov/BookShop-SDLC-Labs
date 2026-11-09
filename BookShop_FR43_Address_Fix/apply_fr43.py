"""Обережне доповнення BookShop для FR-4.3: адреса в профілі та автозаповнення.

Запускати з кореня BookShop-SDLC-Labs:
  python BookShop_FR43_Address_Fix/apply_fr43.py

Працює з уже встановленими файлами лабораторної №5. Жодних змін у БД або .env.
Перед записом перевіряє ВСІ очікувані місця, потім створює резервні копії.
"""
from datetime import datetime
from pathlib import Path
from shutil import copy2
import re

ROOT = Path(__file__).resolve().parent.parent


def once(data: str, old: str, new: str, label: str) -> str:
    count = data.count(old)
    if count != 1:
        raise ValueError(f"{label}: очікувано один збіг, знайдено {count}. Файли не змінені.")
    return data.replace(old, new, 1)


def main() -> None:
    targets = [
        'backend/app/schemas.py',
        'backend/app/routers/auth.py',
        'js/profile.js', 'js/modern-main.js',
        'profile.html', 'css/bookshop-modern.css',
    ]
    original = {}
    for rel in targets:
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"Не знайдено {rel}. Перевір, чи застосовані етап 4 та оновлення дизайну.")
        original[rel] = path.read_text(encoding='utf-8')
    if 'FR43_PROFILE_ADDRESS_PATCH_V1' in original['backend/app/routers/auth.py']:
        raise SystemExit('Оновлення FR-4.3 вже встановлено. Повторно не запускай.')

    changes = {}
    schemas = original['backend/app/schemas.py']
    schemas = once(
        schemas,
        '    phone: str | None = None\n    is_admin: bool\n',
        '    phone: str | None = None\n    address: str | None = None\n    is_admin: bool\n',
        'Схема профілю',
    )
    schemas = once(
        schemas,
        'class LogoutOut(BaseModel):',
        '''class ProfileAddressUpdate(BaseModel):
    address: str = Field(min_length=5, max_length=500)

    @field_validator("address")
    @classmethod
    def normalize_address(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 5:
            raise ValueError("Адреса доставки повинна містити принаймні 5 символів")
        return cleaned


class LogoutOut(BaseModel):''',
        'Схема оновлення адреси',
    )
    changes['backend/app/schemas.py'] = schemas

    auth = original['backend/app/routers/auth.py']
    auth = once(auth, 'UserProfileOut, LogoutOut', 'UserProfileOut, ProfileAddressUpdate, LogoutOut', 'Імпорт схеми')
    auth = once(
        auth,
        '        phone=decrypt_personal_data(user.phone_encrypted) if user.phone_encrypted else None,\n',
        '        phone=decrypt_personal_data(user.phone_encrypted) if user.phone_encrypted else None,\n'
        '        address=decrypt_personal_data(user.address_encrypted) if user.address_encrypted else None,\n',
        'Повернення адреси профілю',
    )
    auth = once(auth, '@router.post("/logout", response_model=LogoutOut)',
        '''# FR43_PROFILE_ADDRESS_PATCH_V1 — server-side address editor with authorization.
@router.patch("/me/address", response_model=UserProfileOut)
def update_profile_address(
    payload: ProfileAddressUpdate,
    identity: Authenticated = Depends(require_authentication),
    db: Session = Depends(get_db),
) -> UserProfileOut:
    identity.user.address_encrypted = encrypt_personal_data(payload.address)
    db.commit()
    db.refresh(identity.user)
    return me(identity)


@router.post("/logout", response_model=LogoutOut)''', 'Endpoint адреси')
    changes['backend/app/routers/auth.py'] = auth

    # Reuse the exact region choices from the already integrated order form.
    index = ROOT / 'index.html'
    if not index.is_file():
        raise SystemExit('Відсутній index.html. Файли не змінені.')
    source = index.read_text(encoding='utf-8')
    match = re.search(r'<select\b[^>]*\bid="region"[^>]*>.*?</select>', source, re.S)
    if not match:
        raise SystemExit('Не знайдено #region у index.html; не змінюй файли вручну — потрібна перевірка версії.')
    region_select = match.group(0).replace('id="region"', 'id="profile-region"').replace('name="region"', 'name="profile-region"')
    profile = original['profile.html']
    if 'id="profile-region"' in profile:
        raise SystemExit('У профілі вже є редагування адреси. Не потрібно дублювати форму.')
    form_html = f'''<section class="profile-address-section" aria-labelledby="profile-address-title">
    <span class="eyebrow">Мої дані</span>
    <h2 id="profile-address-title">Адреса доставки</h2>
    <p id="saved-address" class="profile-address-hint">Завантаження адреси...</p>
    <form id="profile-address-form">
      <div class="profile-address-grid">
        <div class="form-field"><label for="profile-region">Область *</label>{region_select}</div>
        <div class="form-field"><label for="profile-street">Місто / вулиця / будинок *</label>
          <input id="profile-street" type="text" minlength="5" maxlength="400" autocomplete="street-address" required placeholder="м. Хмельницький, вул. ..."></div>
      </div>
      <button class="submit-btn" type="submit">Зберегти адресу</button>
      <p id="profile-address-status" class="form-status" role="status" aria-live="polite"></p>
    </form>
  </section>'''
    profile = once(profile, '<section class="profile-content">', form_html+'<section class="profile-content">', 'Редактор профілю')
    changes['profile.html'] = profile

    js = original['js/profile.js']
    js = once(js, '    if (emailBox) emailBox.textContent = user.email;', '''    if (emailBox) emailBox.textContent = user.email;

    // FR-4.3: show and securely edit the signed-in customer's saved address.
    const addressInfo = document.getElementById("saved-address");
    const regionInput = document.getElementById("profile-region");
    const streetInput = document.getElementById("profile-street");
    const addressStatus = document.getElementById("profile-address-status");
    const form = document.getElementById("profile-address-form");
    function showAddress(address) {
      if (addressInfo) addressInfo.textContent = address || "Адресу ще не збережено";
    }
    showAddress(user.address);
    if (regionInput && streetInput && user.address) {
      const options = Array.from(regionInput.options).filter(option => option.value)
        .sort((a, b) => b.value.length - a.value.length);
      const region = options.find(option => user.address.startsWith(option.value + ", "));
      if (region) {
        regionInput.value = region.value;
        streetInput.value = user.address.slice(region.value.length + 2);
      } else {
        // Legacy address: show it intact; require user to choose a region before saving.
        streetInput.value = user.address;
      }
    }
    form?.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const submit = form.querySelector('button[type="submit"]');
      if (submit) submit.disabled = true;
      if (addressStatus) addressStatus.textContent = "Зберігаємо адресу...";
      try {
        const address = `${regionInput.value}, ${streetInput.value.trim()}`;
        const updated = await BookShopAPI.request("/api/auth/me/address", {
          method: "PATCH", authenticated: true, body: { address }
        });
        showAddress(updated.address);
        if (addressStatus) addressStatus.textContent = "Адресу успішно збережено.";
      } catch (error) {
        if (addressStatus) addressStatus.textContent = `Не вдалося зберегти адресу: ${error.message}`;
      } finally {
        if (submit) submit.disabled = false;
      }
    });''', 'JS профілю')
    changes['js/profile.js'] = js

    main_js = original['js/modern-main.js']
    main_js = once(main_js, '      $("#phone").value = user.phone || "";', '''      $("#phone").value = user.phone || "";
      // FR-4.3: prefill delivery address from the authenticated profile.
      if (user.address) {
        const regionSelect = $("#region");
        const addressInput = $("#address");
        if (regionSelect && addressInput) {
          const options = Array.from(regionSelect.options).filter(option => option.value)
            .sort((a, b) => b.value.length - a.value.length);
          const region = options.find(option => user.address.startsWith(option.value + ", "));
          if (region) {
            regionSelect.value = region.value;
            addressInput.value = user.address.slice(region.value.length + 2);
          } else {
            addressInput.value = user.address;
          }
        }
      }''', 'Автозаповнення замовлення')
    changes['js/modern-main.js'] = main_js

    css = original['css/bookshop-modern.css']
    css += '''\n/* ЛР №5 — FR-4.3: address editor in the personal profile. */
.profile-address-section { margin: 26px 0; padding: 26px; border-radius: 20px;
  border: 1px solid rgba(103,44,59,.15); background: #fffdfb; }
.profile-address-section h2 { margin: 8px 0 6px; font-size: clamp(22px, 2.6vw, 30px); }
.profile-address-hint { margin: 8px 0 18px; overflow-wrap: anywhere; }
.profile-address-grid { display: grid; grid-template-columns: 1fr 1.4fr; gap: 16px; margin-bottom: 16px; }
.profile-address-grid select, .profile-address-grid input { width: 100%; }
@media (max-width: 700px) { .profile-address-grid { grid-template-columns: 1fr; } }
'''
    changes['css/bookshop-modern.css'] = css

    # Validate all edits before writing anything.
    test_source = Path(__file__).resolve().parent / 'test_profile_address.py'
    if not test_source.is_file():
        raise SystemExit('Не знайдено test_profile_address.py у пакеті. Змін не виконано.')
    test_target = ROOT / 'backend/tests/test_profile_address.py'
    if test_target.exists():
        raise SystemExit('Файл тестів адреси вже існує — не перезаписуємо його.')
    changes['backend/tests/test_profile_address.py'] = test_source.read_text(encoding='utf-8')

    backup = ROOT / ('.fr43-address-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir()
    try:
        for rel, content in changes.items():
            target = ROOT / rel
            if target.exists():
                snapshot = backup / rel
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                copy2(target, snapshot)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
    except Exception as exc:
        print('Помилка під час запису; відновлюємо файли зі збережених копій...')
        for rel in changes:
            snapshot = backup / rel
            if snapshot.exists():
                copy2(snapshot, ROOT / rel)
            elif rel not in original and (ROOT / rel).exists():
                (ROOT / rel).unlink()
        raise SystemExit(str(exc)) from exc
    print('Готово! FR-4.3: новий API, форма адреси, автозаповнення та тести.')
    print('Резервна копія:', backup)
    print('PostgreSQL, .env, паролі та секретні ключі не змінено.')
    print('Наступне: cd backend; .\\.venv\\Scripts\\python.exe -m pytest -v')


if __name__ == '__main__':
    main()
