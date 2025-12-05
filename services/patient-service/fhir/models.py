"""FHIR R4 Patient resource models and utilities."""
from typing import Optional, List
from datetime import date, datetime
try:
    from fhir.resources.patient import Patient as FHIRPatient
    from fhir.resources.humanname import HumanName
    from fhir.resources.contactpoint import ContactPoint
    from fhir.resources.address import Address
    from fhir.resources.identifier import Identifier
    from fhir.resources.extension import Extension
    from fhir.resources.fhirtypes import AdministrativeGenderCode
    from fhir.resources.fhirtypes import ContactPointSystemCode
    from fhir.resources.fhirtypes import ContactPointUseCode
except ImportError:
    # Fallback for different fhir.resources versions
    from fhir.resources import Patient as FHIRPatient
    from fhir.resources import HumanName, ContactPoint, Address, Identifier, Extension
    from fhir.resources.fhirtypes import AdministrativeGenderCode, ContactPointSystemCode, ContactPointUseCode

from models import Patient as DBPatient


class FHIRPatientConverter:
    """Converter between database Patient model and FHIR Patient resource."""
    
    @staticmethod
    def db_to_fhir(db_patient: DBPatient) -> FHIRPatient:
        """
        Convert database Patient model to FHIR Patient resource.
        
        Args:
            db_patient: Database Patient model
            
        Returns:
            FHIR Patient resource
        """
        # Create human name
        name_parts = db_patient.full_name.split(maxsplit=1)
        given_names = name_parts[0] if name_parts else []
        family_name = name_parts[1] if len(name_parts) > 1 else name_parts[0] if name_parts else ""
        
        human_name = HumanName(
            use="official",
            family=family_name if len(name_parts) > 1 else None,
            given=[given_names] if given_names else []
        )
        
        # Create identifiers
        identifiers = [
            Identifier(
                use="usual",
                system="http://hospital.example.org/patients",
                value=db_patient.patient_id
            ),
            Identifier(
                use="official",
                system="http://hospital.example.org/patients/email",
                value=db_patient.email
            )
        ]
        
        # Create contact points (phone)
        telecom = []
        if db_patient.phone:
            telecom.append(
                ContactPoint(
                    system=ContactPointSystemCode("phone"),
                    value=db_patient.phone,
                    use=ContactPointUseCode("home")
                )
            )
        
        if db_patient.emergency_contact_phone:
            telecom.append(
                ContactPoint(
                    system=ContactPointSystemCode("phone"),
                    value=db_patient.emergency_contact_phone,
                    use=ContactPointUseCode("mobile")
                )
            )
        
        # Create address
        address = None
        if db_patient.address:
            address = Address(
                use="home",
                text=db_patient.address
            )
        
        # Map gender
        gender = None
        if db_patient.gender:
            gender_map = {
                "Male": AdministrativeGenderCode("male"),
                "Female": AdministrativeGenderCode("female"),
                "Other": AdministrativeGenderCode("other"),
                "Unknown": AdministrativeGenderCode("unknown")
            }
            gender = gender_map.get(db_patient.gender.capitalize(), AdministrativeGenderCode("unknown"))
        
        # Create extensions for custom fields
        extensions = []
        
        # Blood group extension
        if db_patient.blood_group:
            blood_group_ext = Extension(
                url="http://hospital.example.org/fhir/StructureDefinition/blood-group",
                valueString=db_patient.blood_group
            )
            extensions.append(blood_group_ext)
        
        # Allergies extension
        if db_patient.allergies:
            allergies_ext = Extension(
                url="http://hospital.example.org/fhir/StructureDefinition/allergies",
                valueString=db_patient.allergies
            )
            extensions.append(allergies_ext)
        
        # Medical history extension
        if db_patient.medical_history:
            medical_history_ext = Extension(
                url="http://hospital.example.org/fhir/StructureDefinition/medical-history",
                valueString=db_patient.medical_history
            )
            extensions.append(medical_history_ext)
        
        # Current medications extension
        if db_patient.current_medications:
            medications_ext = Extension(
                url="http://hospital.example.org/fhir/StructureDefinition/current-medications",
                valueString=db_patient.current_medications
            )
            extensions.append(medications_ext)
        
        # Emergency contact extension
        if db_patient.emergency_contact_name:
            emergency_contact_ext = Extension(
                url="http://hospital.example.org/fhir/StructureDefinition/emergency-contact",
                valueString=f"{db_patient.emergency_contact_name} ({db_patient.emergency_contact_phone or 'N/A'})"
            )
            extensions.append(emergency_contact_ext)
        
        # Active status extension
        active_ext = Extension(
            url="http://hospital.example.org/fhir/StructureDefinition/active-status",
            valueBoolean=db_patient.is_active
        )
        extensions.append(active_ext)
        
        # Create FHIR Patient resource
        fhir_patient = FHIRPatient(
            resource_type="Patient",
            id=db_patient.patient_id,
            identifier=identifiers,
            name=[human_name],
            telecom=telecom if telecom else None,
            gender=gender,
            birthDate=db_patient.date_of_birth.isoformat() if db_patient.date_of_birth else None,
            address=[address] if address else None,
            extension=extensions if extensions else None,
            active=db_patient.is_active
        )
        
        # Add meta information
        fhir_patient.meta = {
            "versionId": "1",
            "lastUpdated": db_patient.updated_at.isoformat() if db_patient.updated_at else datetime.utcnow().isoformat(),
            "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]
        }
        
        return fhir_patient
    
    @staticmethod
    def fhir_to_db(fhir_patient: FHIRPatient) -> dict:
        """
        Convert FHIR Patient resource to database Patient model dictionary.
        
        Args:
            fhir_patient: FHIR Patient resource
            
        Returns:
            Dictionary with patient data for database model
        """
        # Extract name
        full_name = ""
        if fhir_patient.name and len(fhir_patient.name) > 0:
            name = fhir_patient.name[0]
            given = " ".join(name.given) if name.given else ""
            family = name.family or ""
            full_name = f"{given} {family}".strip()
        
        # Extract email from identifiers
        email = ""
        if fhir_patient.identifier:
            for identifier in fhir_patient.identifier:
                if identifier.system and "email" in identifier.system:
                    email = identifier.value or ""
                    break
        
        # Extract phone from telecom
        phone = None
        emergency_contact_phone = None
        emergency_contact_name = None
        if fhir_patient.telecom:
            for contact in fhir_patient.telecom:
                if contact.system == "phone":
                    if contact.use == "home":
                        phone = contact.value
                    elif contact.use == "mobile":
                        emergency_contact_phone = contact.value
        
        # Extract address
        address = None
        if fhir_patient.address and len(fhir_patient.address) > 0:
            address = fhir_patient.address[0].text
        
        # Extract gender
        gender = None
        if fhir_patient.gender:
            gender_map = {
                "male": "Male",
                "female": "Female",
                "other": "Other",
                "unknown": "Unknown"
            }
            gender = gender_map.get(fhir_patient.gender.value.lower(), "Unknown")
        
        # Extract date of birth
        date_of_birth = None
        if fhir_patient.birthDate:
            date_of_birth = date.fromisoformat(fhir_patient.birthDate)
        
        # Extract custom fields from extensions
        blood_group = None
        allergies = None
        medical_history = None
        current_medications = None
        
        if fhir_patient.extension:
            for ext in fhir_patient.extension:
                if ext.url and "blood-group" in ext.url:
                    blood_group = ext.valueString
                elif ext.url and "allergies" in ext.url:
                    allergies = ext.valueString
                elif ext.url and "medical-history" in ext.url:
                    medical_history = ext.valueString
                elif ext.url and "current-medications" in ext.url:
                    current_medications = ext.valueString
                elif ext.url and "emergency-contact" in ext.url:
                    emergency_contact = ext.valueString
                    if emergency_contact:
                        # Parse "Name (Phone)" format
                        if "(" in emergency_contact:
                            parts = emergency_contact.split("(")
                            emergency_contact_name = parts[0].strip()
                            emergency_contact_phone = parts[1].replace(")", "").strip() if len(parts) > 1 else None
        
        # Extract patient_id from identifiers
        patient_id = None
        if fhir_patient.identifier:
            for identifier in fhir_patient.identifier:
                if identifier.system and "patients" in identifier.system and "email" not in identifier.system:
                    patient_id = identifier.value
                    break
        
        # Extract active status
        is_active = fhir_patient.active if fhir_patient.active is not None else True
        
        return {
            "patient_id": patient_id or fhir_patient.id,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "date_of_birth": date_of_birth,
            "gender": gender,
            "address": address,
            "blood_group": blood_group,
            "allergies": allergies,
            "medical_history": medical_history,
            "current_medications": current_medications,
            "emergency_contact_name": emergency_contact_name,
            "emergency_contact_phone": emergency_contact_phone,
            "is_active": is_active
        }


class FHIRValidator:
    """FHIR resource validation utilities."""
    
    @staticmethod
    def validate_fhir_patient(fhir_patient: FHIRPatient) -> tuple[bool, Optional[str]]:
        """
        Validate FHIR Patient resource.
        
        Args:
            fhir_patient: FHIR Patient resource to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check resource type
        if fhir_patient.resource_type != "Patient":
            return False, "Resource type must be 'Patient'"
        
        # Check required fields
        if not fhir_patient.name or len(fhir_patient.name) == 0:
            return False, "Patient must have at least one name"
        
        # Check identifier
        if not fhir_patient.identifier or len(fhir_patient.identifier) == 0:
            return False, "Patient must have at least one identifier"
        
        # Validate email identifier
        has_email = False
        for identifier in fhir_patient.identifier:
            if identifier.system and "email" in identifier.system:
                if not identifier.value or "@" not in identifier.value:
                    return False, "Invalid email identifier"
                has_email = True
        
        if not has_email:
            return False, "Patient must have an email identifier"
        
        return True, None

