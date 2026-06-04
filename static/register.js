// Same autofill fix as login — some browsers don't fire 'input' on autofill
document.addEventListener('animationstart', function (e) {
  if (e.animationName === 'onAutoFillStart') {
    validateEmail(false);
    updateSignupButton();
  }
}, true);

window.addEventListener('load', function () {
  let checks = 0;
  const interval = setInterval(function () {
    const email = document.getElementById('email');
    const pw = document.getElementById('password');
    if (email.value || pw.value) {
      validateEmail(false);
      updateSignupButton();
    }
    if (++checks >= 20) clearInterval(interval);
  }, 100);
});

function validateEmail(showError) {
  const emailInput = document.getElementById('email');
  const emailError = document.getElementById('email-error');
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  const isValid = pattern.test(emailInput.value);

  if (isValid || emailInput.value.length === 0) {
    emailError.classList.add('hidden');
    emailInput.classList.remove('invalid');
  } else if (showError) {
    emailError.classList.remove('hidden');
    emailInput.classList.add('invalid');
  }
  updateSignupButton();
}

function checkPasswordRequirements(password) {
  const requirements = {
    length:  password.length >= 8,
    upper:   /[A-Z]/.test(password),
    lower:   /[a-z]/.test(password),
    number:  /\d/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
  };

  document.getElementById('req-length').classList.toggle('valid', requirements.length);
  document.getElementById('req-upper').classList.toggle('valid', requirements.upper);
  document.getElementById('req-lower').classList.toggle('valid', requirements.lower);
  document.getElementById('req-number').classList.toggle('valid', requirements.number);
  document.getElementById('req-special').classList.toggle('valid', requirements.special);

  return Object.values(requirements).every(Boolean);
}

function validatePassword() {
  checkPasswordRequirements(document.getElementById('password').value);
  updateSignupButton();
}

function validateConfirmPassword() {
  const confirmInput = document.getElementById('confirm-password');
  const confirmError = document.getElementById('confirm-password-error');
  const pw = document.getElementById('password').value;

  if (confirmInput.value && pw === confirmInput.value) {
    confirmError.classList.add('hidden');
    confirmInput.classList.remove('invalid');
  }
  updateSignupButton();
}

function updateSignupButton() {
  const email = document.getElementById('email').value;
  const pw = document.getElementById('password').value;
  const confirmPw = document.getElementById('confirm-password').value;
  const signupButton = document.getElementById('signup-button');
  signupButton.disabled = !(email && pw && confirmPw);
}

function submitSignup(e) {
  e.preventDefault();

  validateEmail(true);

  const pw = document.getElementById('password');
  const confirmPw = document.getElementById('confirm-password');
  const confirmError = document.getElementById('confirm-password-error');
  const signupText = document.getElementById('signup-text');
  const signupSpinner = document.getElementById('signup-spinner');
  const signupButton = document.getElementById('signup-button');

  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!pattern.test(document.getElementById('email').value)) return;
  if (!checkPasswordRequirements(pw.value)) return;

  if (pw.value !== confirmPw.value) {
    confirmError.classList.remove('hidden');
    confirmPw.classList.add('invalid');
    return;
  }

  if (!signupButton.disabled) {
    signupText.classList.add('hidden');
    signupSpinner.classList.remove('hidden');
    e.target.submit();
  }
}

document.getElementById('email').addEventListener('input', function () { validateEmail(false); });
document.getElementById('email').addEventListener('blur', function () { validateEmail(true); });
document.getElementById('password').addEventListener('input', validatePassword);
document.getElementById('confirm-password').addEventListener('input', validateConfirmPassword);
document.getElementById('signupForm').addEventListener('submit', submitSignup);
