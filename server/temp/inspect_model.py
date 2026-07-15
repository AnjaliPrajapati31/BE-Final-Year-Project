import joblib

model = joblib.load("ml_models/soilfertility.pkl")

print(type(model))
print(model)