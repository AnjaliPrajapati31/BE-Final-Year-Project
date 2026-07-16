from tensorflow import keras

model = keras.models.load_model("ml_models/disease.keras")

print("=" * 70)
print("MODEL TYPE")
print("=" * 70)
print(type(model))

print("\n" + "=" * 70)
print("MODEL NAME")
print("=" * 70)
print(model.name)

print("\n" + "=" * 70)
print("INPUT SHAPE")
print("=" * 70)
print(model.input_shape)

print("\n" + "=" * 70)
print("OUTPUT SHAPE")
print("=" * 70)
print(model.output_shape)

print("\n" + "=" * 70)
print("TOTAL PARAMETERS")
print("=" * 70)
print(model.count_params())

print("\n" + "=" * 70)
print("MODEL SUMMARY")
print("=" * 70)
model.summary()

print("\n" + "=" * 70)
print("LAYERS")
print("=" * 70)

for i, layer in enumerate(model.layers):
    print(f"\nLayer {i+1}")
    print(f"Name       : {layer.name}")
    print(f"Type       : {layer.__class__.__name__}")

    if hasattr(layer, "input_shape"):
        print(f"Input      : {layer.input_shape}")

    if hasattr(layer, "output_shape"):
        print(f"Output     : {layer.output_shape}")

    print(f"Trainable  : {layer.trainable}")

print("\n" + "=" * 70)
print("INPUT DTYPE")
print("=" * 70)
print(model.input_dtype)

print("\n" + "=" * 70)
print(model.outputs)