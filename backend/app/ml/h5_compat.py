"""Compatibility objects for legacy Keras H5 serialization."""

from __future__ import annotations

from typing import Any


def h5_custom_objects(tf: Any) -> dict[str, type]:
    """Return safe compatibility layers needed by the supplied H5 artifact.

    The training artifact serializes the residual ``Add`` layer with two
    positional inbound tensors. Newer Keras versions deserialize ``Add`` as a
    single-list-input layer. This replacement performs the same elementwise
    sum and contains no trainable parameters; it only restores the old graph
    wiring so the original weights can be loaded.

    Parameters
    ----------
    tf : module
        Imported TensorFlow module, kept as an argument so normal stub-only
        installations do not import TensorFlow.

    Returns
    -------
    dict[str, type]
        Custom-object mapping for ``tf.keras.models.load_model``.
    """

    from keras import KerasTensor

    class LegacyAdd(tf.keras.layers.Layer):
        """Deserialize the artifact's two-input residual addition."""

        def call(self, *inputs: Any, **kwargs: Any) -> Any:
            """Return the elementwise sum of the inbound tensors."""

            values = inputs[0] if len(inputs) == 1 and isinstance(inputs[0], (list, tuple)) else inputs
            return tf.add_n(values)

        def compute_output_spec(self, *inputs: Any, **kwargs: Any) -> Any:
            """Describe the residual tensor for Keras symbolic graph loading."""

            first = inputs[0]
            return KerasTensor(shape=first.shape, dtype=first.dtype)

    return {"Add": LegacyAdd}
