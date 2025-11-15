# DSPy Gemini Integration Guide

**Document Version:** 1.0
**Date:** November 15, 2025

## 1. Overview

This document outlines the correct method for integrating Google's Gemini models with the DSPy library, based on recent findings and official examples. The key takeaway is that DSPy uses a generic `dspy.LM` loader class rather than a model-specific one like `dspy.Google`.

## 2. Correct Implementation

To configure DSPy to use a Gemini model, you must instantiate `dspy.LM` and pass the model name and API key directly to it.

### Code Example:

```python
import os
import dspy

# 1. Get the API key from environment variables.
api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    # 2. Instantiate the language model using dspy.LM with the model name.
    # The model name should be in the format "provider/model_name".
    lm = dspy.LM("gemini/gemini-1.5-flash-latest", api_key=api_key)
    
    # 3. Configure DSPy's global settings to use this language model.
    dspy.settings.configure(lm=lm)
    
    print("DSPy configured successfully with Gemini model.")
else:
    print("GOOGLE_API_KEY not found. DSPy will not be configured.")

```

## 3. Key Findings

-   **Generic Loader**: The primary class for loading language models is `dspy.LM`.
-   **Model Naming Convention**: The model is specified with a string identifier in the format `"provider/model_name"`, for example, `"gemini/gemini-1.5-flash-latest"`.
-   **API Key**: The `api_key` is passed directly during the instantiation of the `dspy.LM` object.

## 4. Action Plan

The `CoordinatorAgent` in `src/agents/coordinator.py` will be updated to reflect this correct implementation. The previous attempt to use `dspy.Google` was incorrect and will be replaced with the `dspy.LM` pattern. This will resolve the `AttributeError` observed during unit testing.
