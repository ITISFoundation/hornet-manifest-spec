# [HORNET] Manifests Specification

The [HORNET] Manifest Specification provides standardized formats for describing CAD components and preparing them for computational simulations. Through interconnected JSON schemas, it enables:

* 🌐 **Discoverability** — Enables services to index CAD assets and integrate them into simulation workflows
* 🔄 **Interoperability** — Components can be referenced across tools and platforms
* 📂 **Structure** — Hierarchical organization of components for simulation setups
* 💾 **Consistency** — Schema validation ensures data integrity and prevents errors
* 🧪 **Simulation-Ready** — Comprehensive preparation of CAD components for numerical analysis


## 🔗 At a Glance

**Creating CAD and Simulation Manifests in your repository:**


1. **CAD Manifest** (`.hornet/cad_manifest.json`) - Describes your CAD components, assemblies, and files
   * Include `"$schema": "https://raw.githubusercontent.com/ITISFoundation/hornet-manifest-spec/refs/heads/main/schema/cad_manifest.schema.json"`
   * Define components with IDs, types, descriptions, and file references

2. **Simulation Manifest** (`.hornet/sim_manifest.json`) - Prepares CAD components for simulation use
   * Include `"$schema": "https://raw.githubusercontent.com/ITISFoundation/hornet-manifest-spec/refs/heads/main/schema/sim_manifest.schema.json"`
   * Reference components from your CAD manifest and define their simulation context (materials, boundary conditions, etc.)

3. **Validate** using VS Code, GitHub Actions, pre-commit hooks, or online tools
   * All validation uses the same JSON Schemas for consistent results

4. **Github Topic** optionally add the topic [`#hornet-manifests`](https://github.com/topics/hornet-manifests) to [classify your github repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/classifying-your-repository-with-topics)


> NOTE: All manifest files (such as `cad_manifest.json` and `sim_manifest.json`) **must be placed inside a folder named `.hornet` at the root of your repository**. For  example: `.hornet/cad_manifest.json` and `.hornet/sim_manifest.json`.


---

## 📋 What's in this Repository

This repository contains:

* 🧩 **JSON Schemas** for manifests:
  * [`schema/cad_manifest.schema.json`](schema/cad_manifest.schema.json) - For describing CAD components
  * [`schema/sim_manifest.schema.json`](schema/sim_manifest.schema.json) - For mapping CAD components to simulation properties
* 📝 **Examples** of valid manifest files at [`examples/`](examples/)
* 📚 **Vocabularies** at [`vocab/`](vocab/) for standardized terms
* 🛠️ **Validation tools** and instructions for integration

### 🧩 JSON Schemas

#### CAD Manifest Schema

A **JSON Schema** describing how to create a valid `cad_manifest.json`.
It standardizes:

* ⚙️ A **tree-like structure** of `components`, including assemblies and parts
* ℹ️ Component **metadata** (id, type, description, files)
* 🧰 File references (paths and types like STEP/SolidWorks)


#### Simulation Manifest Schema

A **JSON Schema** describing how to create a valid `sim_manifest.json`.
It standardizes:

* 🔗 **Component references** to CAD definitions for simulation use
* 🧪 **Material assignments** for physical property calculations
* 🛠️ **Boundary conditions** for defining simulation domains and constraints
* 🏷️ **Semantic tags** for simulation-specific categorization and processing

The simulation manifest transforms CAD components into simulation-ready definitions, enabling direct incorporation into computational models without manual translation steps.

### 📚 Vocabulary Files

This specification includes standardized vocabularies to ensure consistency:

* [`vocab/semantic-tags.json`](vocab/semantic-tags.json) - Defines standardized tags for component roles (e.g., "electrical_interface", "biocompatible")
* [`vocab/boundary-conditions.json`](vocab/boundary-conditions.json) - Defines standardized boundary conditions for simulations (e.g., "electrical_contact", "insulating")

These vocabularies:

* Ensure consistent terminology across projects
* Allow validation of correct tag/condition usage
* Can be extended as needs evolve

### 💡 Simple Example

Here's a minimal example of a valid `.hornet/cad_manifest.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/ITISFoundation/hornet-manifest-spec/refs/heads/main/schema/cad_manifest.schema.json",
  "repository": "https://github.com/myorg/cad-project",
  "components": [
    {
      "id": "SimpleAssembly",
      "type": "assembly",
      "description": "A basic assembly with one part",
      "files": [
        { "path": "assemblies/SimpleAssembly.SLDASM", "type": "solidworks_assembly" }
      ],
      "components": [
        {
          "id": "SimplePart",
          "type": "part",
          "description": "A basic part component",
          "files": [
            { "path": "parts/SimplePart.SLDPRT", "type": "solidworks_part" },
            { "path": "exports/SimplePart.step", "type": "step_export" }
          ]
        }
      ]
    }
  ]
}
```

For more complex examples, see the [`examples/`](examples/) directory. In your own repository, always place your manifest files in the `.hornet/` folder.

#### Simulation Manifest Example

Here's a minimal example of a valid `.hornet/sim_manifest.json`:

```json
{
  "$schema": "https://raw.githubusercontent.com/ITISFoundation/hornet-manifest-spec/refs/heads/main/schema/sim_manifest.schema.json",
  "mappings": [
    {
      "component_ref": {
        "cad_manifest_path": ".hornet/cad_manifest.json",
        "component_id": "SimplePart"
      },
      "material": {
        "name": "Titanium"
      },
      "boundary_conditions": ["insulating"],
      "tags": ["biocompatible"]
    }
  ]
}
```

This example maps a CAD component to its simulation-specific context, defining material properties and boundary conditions needed for computational analysis. Note that the `cad_manifest_path` points to the manifest inside the `.hornet` folder.

### 🔄 Keeping Schemas and Vocabularies in Sync

The repository includes an automated sync mechanism:

* The script [`scripts/sync_vocab_to_schema.py`](scripts/sync_vocab_to_schema.py) ensures vocabulary terms are reflected in schema validation rules
* A pre-commit hook automatically runs this script to maintain synchronization
* This prevents vocabulary/schema drift and ensures consistent validation

### 🛠️ Different Ways to Validate your Manifests

<img src="https://json-schema.org/img/json_schema.svg" alt="Schema validation" width="50%" />

#### 1. ✅ In VS Code

Ensure your manifest is located in `.hornet/` and begins like this:

```json
{
  "$schema": "https://raw.githubusercontent.com/ITISFoundation/hornet-manifest-spec/refs/heads/main/schema/cad_manifest.schema.json",
  "repository": "...",
  "components": [ ... ]
}
```

VS Code (with built‑in JSON support) will:

* Fetch the schema automatically
* Show red squiggles for structural issues
* Offer autocompletion


#### 2. ✅ Using GitHub Actions

Add this workflow to `.github/workflows/validate-manifest.yml` to your repo:

```yaml
- name: Checkout code
  uses: actions/checkout@v3

- name: Install JSON Schema CLI
  uses: sourcemeta/jsonschema@v11.0.0

- name: Validate CAD manifest
  run: |
    schema_url=$(jq -r '.["$schema"]' .hornet/cad_manifest.json)
    curl -o cad_schema.json "$schema_url"
    jsonschema validate cad_schema.json .hornet/cad_manifest.json --json

- name: Validate Sim manifest
  run: |
    schema_url=$(jq -r '.["$schema"]' .hornet/sim_manifest.json)
    curl -o sim_schema.json "$schema_url"
    jsonschema validate sim_schema.json .hornet/sim_manifest.json --json
```

This uses:

* 📥 `curl` to download the schema files locally
* ⚖️ `sourcemeta/jsonschema@v11.0.0` with local schema files and the correct command syntax
* 📝 Validates both CAD and Sim manifests


#### 3. ✅ As a Pre-commit Hook

Add to your `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/python-jsonschema/check-jsonschema
    rev: 0.33.0
    hooks:
      - id: check-jsonschema
        name: Validate CAD Manifest
        args: ["--schemafile", "cad_manifest.schema.json"]
        files: ^\.hornet/cad_manifest\.json$
```

This runs validation on staged edits to `cad_manifest.json` before commits.


#### 4. ✅ Online Validator

Use tools like:

* [**JSONSchema.dev**](https://jsonschema.dev/)
* [**JSON Schema Validator**](https://www.jsonschemavalidator.net/)

You can:

* Paste your `cad_manifest.json`
* Or load from URL
* The schema is fetched from its `$schema` header automatically


### 🎨 Generate UIs from the JSON Schema

You can automatically create user interfaces for editing `cad_manifest.json` files using these tools:

* **[JSON Schema Form Playground](https://rjsf-team.github.io/react-jsonschema-form/)** — Test RJSF instantly



## Contributing

Contributions to improve the schema are welcome. Please submit a pull request with your proposed changes.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Copyright

Copyright (c) 2025 IT'IS Foundation

[HORNET]:https://www.ninds.nih.gov/current-research/research-funded-ninds/translational-research/translational-devices/human-open-research-neural-engineering-technologies-hornet-initiative

<p align="center">
<a href="https://www.z43.swiss" target="_blank">
<image src="https://github.com/ITISFoundation/hornet-manifest-spec/blob/main/doc/img/mwl.png?raw=true" alt="Made with lots of Love (and hard work) at www.z43.swiss" width="20%" />
</a>
</p>
