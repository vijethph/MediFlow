// Database Initialization Script for Prescription Service (MongoDB)
// Reusable for local development, Docker, and Kubernetes environments

print("Initializing Prescription Service Database...");

// Switch to prescription database
db = db.getSiblingDB("prescription_db");

// Create collections with validation if they don't exist
try {
  // Prescriptions collection
  db.createCollection("prescriptions", {
    validator: {
      $jsonSchema: {
        bsonType: "object",
        required: [
          "prescription_id",
          "patient_id",
          "doctor_name",
          "prescription_date",
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
          prescription_date: {
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

  // Create indexes
  db.prescriptions.createIndex({ prescription_id: 1 }, { unique: true });
  db.prescriptions.createIndex({ patient_id: 1 });
  db.prescriptions.createIndex({ prescription_date: -1 });
  db.prescriptions.createIndex({ status: 1 });

  print("Prescriptions collection created with indexes");
} catch (e) {
  if (e.code !== 48) {
    // Collection already exists
    print("Error creating prescriptions collection: " + e);
  } else {
    print("Prescriptions collection already exists");
  }
}

try {
  // Lab Results collection
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

  // Create indexes
  db.lab_results.createIndex({ result_id: 1 }, { unique: true });
  db.lab_results.createIndex({ patient_id: 1 });
  db.lab_results.createIndex({ result_date: -1 });
  db.lab_results.createIndex({ status: 1 });

  print("Lab Results collection created with indexes");
} catch (e) {
  if (e.code !== 48) {
    // Collection already exists
    print("Error creating lab_results collection: " + e);
  } else {
    print("Lab Results collection already exists");
  }
}

try {
  // Medical Records collection
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

  // Create indexes
  db.medical_records.createIndex({ record_id: 1 }, { unique: true });
  db.medical_records.createIndex({ patient_id: 1 });
  db.medical_records.createIndex({ record_date: -1 });
  db.medical_records.createIndex({ record_type: 1 });

  print("Medical Records collection created with indexes");
} catch (e) {
  if (e.code !== 48) {
    // Collection already exists
    print("Error creating medical_records collection: " + e);
  } else {
    print("Medical Records collection already exists");
  }
}

// Optional: Seed data for development
if (process.env.SEED_DATA === "true") {
  print("Seeding development data...");

  // Add sample data here if needed

  print("Seed data inserted.");
}

print("Prescription Service database initialization complete!");
