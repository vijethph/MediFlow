// Database Initialization Script for Prescription Service (MongoDB)
// Reusable for local development, Docker, and Kubernetes environments

print("Initializing Prescription Service Database...");

db = db.getSiblingDB("prescription_db");

try {
  db.createCollection("prescriptions", {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: [
          "prescription_id",
          "patient_id",
          "doctor_name",
          "prescribed_date",
        ],
        properties: {
          prescription_id: {
            bsonType: "string",
            description: "Unique prescription identifier",
          },
          patient_id: {
            bsonType: "string",
            description: "Patient identifier",
          },
          doctor_name: {
            bsonType: "string",
            description: "Prescribing doctor name",
          },
          prescribed_date: {
            bsonType: "date",
            description: "Date of prescription",
          },
          status: {
            enum: [
              "active",
              "completed",
              "cancelled",
              "entered-in-error",
              "stopped",
            ],
            description: "Prescription status",
          },
        },
      },
    },
  });

  db.prescriptions.createIndex({ prescription_id: 1 }, { unique: true });
  db.prescriptions.createIndex({ patient_id: 1 });
  db.prescriptions.createIndex({ prescribed_date: -1 });
  db.prescriptions.createIndex({ status: 1 });

  print("Prescriptions collection created with indexes");
} catch (e) {
  if (e.code !== 48) {
    print("Error creating prescriptions collection: " + e);
  } else {
    print("Prescriptions collection already exists");
  }
}

try {
  db.createCollection("lab_results", {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: ["result_id", "patient_id", "test_name", "result_date"],
        properties: {
          result_id: {
            bsonType: "string",
            description: "Unique lab result identifier",
          },
          patient_id: {
            bsonType: "string",
            description: "Patient identifier",
          },
          test_name: {
            bsonType: "string",
            description: "Name of the test",
          },
          result_date: {
            bsonType: "date",
            description: "Date of result",
          },
          status: {
            enum: [
              "registered",
              "preliminary",
              "final",
              "amended",
              "corrected",
              "cancelled",
            ],
            description: "Result status",
          },
        },
      },
    },
  });

  db.lab_results.createIndex({ result_id: 1 }, { unique: true });
  db.lab_results.createIndex({ patient_id: 1 });
  db.lab_results.createIndex({ result_date: -1 });
  db.lab_results.createIndex({ status: 1 });

  print("Lab Results collection created with indexes");
} catch (e) {
  if (e.code !== 48) {
    print("Error creating lab_results collection: " + e);
  } else {
    print("Lab Results collection already exists");
  }
}

try {
  db.createCollection("medical_records", {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: ["record_id", "patient_id", "record_type", "record_date"],
        properties: {
          record_id: {
            bsonType: "string",
            description: "Unique medical record identifier",
          },
          patient_id: {
            bsonType: "string",
            description: "Patient identifier",
          },
          record_type: {
            enum: [
              "consultation",
              "diagnosis",
              "procedure",
              "imaging",
              "discharge_summary",
              "progress_note",
            ],
            description: "Type of medical record",
          },
          record_date: {
            bsonType: "date",
            description: "Date of record",
          },
        },
      },
    },
  });

  db.medical_records.createIndex({ record_id: 1 }, { unique: true });
  db.medical_records.createIndex({ patient_id: 1 });
  db.medical_records.createIndex({ record_date: -1 });
  db.medical_records.createIndex({ record_type: 1 });

  print("Medical Records collection created with indexes");
} catch (e) {
  if (e.code !== 48) {
    print("Error creating medical_records collection: " + e);
  } else {
    print("Medical Records collection already exists");
  }
}

if (process.env.SEED_DATA === "true") {
  print("Seeding prescription data from CSV files...");

  const prescriptionFile = "/docker-entrypoint-initdb.d/prescription_data.csv";
  const medicationFile = "/docker-entrypoint-initdb.d/medication_data.csv";

  try {
    const prescriptionLines = cat(prescriptionFile).split("\n");
    const medicationLines = cat(medicationFile).split("\n");

    const prescriptionHeaders = prescriptionLines[0].split(",");
    const medicationHeaders = medicationLines[0].split(",");

    const prescriptionData = [];
    for (let i = 1; i < prescriptionLines.length; i++) {
      if (!prescriptionLines[i].trim()) continue;

      const csvLine = prescriptionLines[i];
      const values = [];
      let currentValue = "";
      let insideQuotes = false;

      for (let j = 0; j < csvLine.length; j++) {
        const char = csvLine[j];
        if (char === '"') {
          insideQuotes = !insideQuotes;
        } else if (char === "," && !insideQuotes) {
          values.push(currentValue.trim());
          currentValue = "";
        } else {
          currentValue += char;
        }
      }
      values.push(currentValue.trim());

      const prescription = {
        prescription_id: values[0] || "",
        patient_id: values[1] || "",
        appointment_id: values[2] || null,
        doctor_name: values[3] || "",
        doctor_id: values[4] || null,
        diagnosis: values[5] || "",
        status: values[6] || "active",
        prescribed_date: values[7] ? new Date(values[7]) : new Date(),
        valid_until: values[8] ? new Date(values[8]) : null,
        follow_up_required: values[9] === "true" || values[9] === "TRUE",
        follow_up_days: values[10] ? parseInt(values[10]) : null,
        notes: values[11] || null,
      };

      prescriptionData.push(prescription);
    }

    const medicationMap = {};
    for (let i = 1; i < medicationLines.length; i++) {
      if (!medicationLines[i].trim()) continue;

      const csvLine = medicationLines[i];
      const values = [];
      let currentValue = "";
      let insideQuotes = false;

      for (let j = 0; j < csvLine.length; j++) {
        const char = csvLine[j];
        if (char === '"') {
          insideQuotes = !insideQuotes;
        } else if (char === "," && !insideQuotes) {
          values.push(currentValue.trim());
          currentValue = "";
        } else {
          currentValue += char;
        }
      }
      values.push(currentValue.trim());

      const prescriptionId = values[1] || "";
      const medication = {
        medication_name: values[2] || "",
        dosage: values[3] || "",
        frequency: values[4] || "once_daily",
        duration_days: values[5] ? parseInt(values[5]) : 30,
        quantity: values[6] ? parseInt(values[6]) : null,
        instructions: values[7] || null,
      };

      if (!medicationMap[prescriptionId]) {
        medicationMap[prescriptionId] = [];
      }
      medicationMap[prescriptionId].push(medication);
    }

    let insertedCount = 0;
    for (const prescription of prescriptionData) {
      const medications = medicationMap[prescription.prescription_id] || [];
      prescription.medications = medications;
      prescription.meta = {};
      prescription.created_at = new Date();
      prescription.updated_at = new Date();

      try {
        db.prescriptions.insertOne(prescription);
        insertedCount++;
      } catch (e) {
        if (e.code !== 11000) {
          print(
            "Error inserting prescription " +
              prescription.prescription_id +
              ": " +
              e
          );
        }
      }
    }

    print(insertedCount + " prescriptions inserted");
  } catch (e) {
    print("Error loading CSV files: " + e);
    print("Make sure CSV files are mounted in /docker-entrypoint-initdb.d/");
  }
}

print("Prescription Service database initialization complete!");
