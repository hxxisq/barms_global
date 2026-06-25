import streamlit_authenticator as stauth

# Type the 3 passwords you want to give your team here
passwords = ["admin"]

# The new, updated syntax for hashing a list
hashed_passwords = stauth.Hasher.hash_list(passwords)
print(hashed_passwords)