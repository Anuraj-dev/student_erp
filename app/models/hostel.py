from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app import db


class Hostel(db.Model):
    """Hostel model for student accommodation"""
    
    __tablename__ = 'hostels'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Hostel details
    name = Column(String(100), nullable=False, unique=True)
    hostel_type = Column(String(20), nullable=False)  # Boys, Girls, Mixed
    warden_name = Column(String(100))
    warden_phone = Column(String(15))
    
    # Capacity details
    total_beds = Column(Integer, nullable=False)
    occupied_beds = Column(Integer, nullable=False, default=0)
    
    # Location and facilities
    address = Column(Text)
    facilities = Column(Text)  # JSON string of facilities
    mess_facility = Column(Boolean, default=True, nullable=False)
    wifi_available = Column(Boolean, default=True, nullable=False)
    
    # Fees
    monthly_rent = Column(Integer, nullable=False, default=3000)  # In rupees
    security_deposit = Column(Integer, nullable=False, default=10000)  # In rupees
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_on = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_on = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    students = relationship('Student', back_populates='hostel', lazy='dynamic')
    
    def __repr__(self):
        return f'<Hostel {self.name}: {self.available_beds}/{self.total_beds} available>'
    
    @property
    def available_beds(self):
        """Calculate available beds"""
        return self.total_beds - self.occupied_beds
    
    def to_dict(self):
        """Convert hostel object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'hostel_type': self.hostel_type,
            'warden_name': self.warden_name,
            'warden_phone': self.warden_phone,
            'total_beds': self.total_beds,
            'occupied_beds': self.occupied_beds,
            'available_beds': self.available_beds,
            'address': self.address,
            'facilities': self.facilities,
            'mess_facility': self.mess_facility,
            'wifi_available': self.wifi_available,
            'monthly_rent': self.monthly_rent,
            'security_deposit': self.security_deposit,
            'is_active': self.is_active,
            'created_on': self.created_on.isoformat() if self.created_on else None,
            'updated_on': self.updated_on.isoformat() if self.updated_on else None
        }
    
    @staticmethod
    def get_available_hostels(gender=None):
        """Get hostels with available beds"""
        query = Hostel.query.filter(
            Hostel.is_active == True,
            Hostel.total_beds > Hostel.occupied_beds
        )
        
        if gender:
            if gender.lower() == 'male':
                query = query.filter(Hostel.hostel_type.in_(['Boys', 'Mixed']))
            elif gender.lower() == 'female':
                query = query.filter(Hostel.hostel_type.in_(['Girls', 'Mixed']))
        
        return query.all()
    
    def has_available_beds(self):
        """Check if hostel has available beds"""
        return self.available_beds > 0
    
    def allocate_bed(self):
        """Allocate a bed (increment occupied count)"""
        if self.has_available_beds():
            self.occupied_beds += 1
            db.session.commit()
            return True
        return False
    
    def vacate_bed(self):
        """Vacate a bed (decrement occupied count)"""
        if self.occupied_beds > 0:
            self.occupied_beds -= 1
            db.session.commit()
            return True
        return False
    
    def get_occupancy_percentage(self):
        """Get occupancy percentage"""
        if self.total_beds == 0:
            return 0
        return round((self.occupied_beds / self.total_beds) * 100, 2)
    
    @staticmethod
    def get_occupancy_stats():
        """Get overall hostel occupancy statistics"""
        hostels = Hostel.query.filter_by(is_active=True).all()
        total_beds = sum(h.total_beds for h in hostels)
        total_occupied = sum(h.occupied_beds for h in hostels)
        
        return {
            'total_hostels': len(hostels),
            'total_beds': total_beds,
            'total_occupied': total_occupied,
            'total_available': total_beds - total_occupied,
            'occupancy_percentage': round((total_occupied / total_beds) * 100, 2) if total_beds > 0 else 0
        }
