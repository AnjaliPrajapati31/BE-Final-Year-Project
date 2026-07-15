import joblib

model = joblib.load("ml_models/soilfertility.pkl")

print("Type:", type(model))
print()

print("Model:")
print(model)
print()

print("Attributes")
print("-" * 40)

attributes = [
    "feature_names_in_",
    "n_features_in_",
    "classes_",
]

for attr in attributes:
    if hasattr(model, attr):
        print(attr)
        print(getattr(model, attr))
        print()