from sqlalchemy import Column, Integer, String, DateTime, Date, Time, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(Base, UserMixin):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False) # Consider making this longer, e.g. String(256)
    role = Column(String(50)) # e.g., 'admin', 'staff'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Passenger(Base):
    __tablename__ = 'passengers'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    flight_number = Column(String(50))
    lounge_entries = relationship("LoungeEntry", back_populates="passenger")

    def __repr__(self):
        return f'<Passenger {self.name}>'

class LoungeEntry(Base):
    __tablename__ = 'lounge_entries'
    id = Column(Integer, primary_key=True)
    passenger_id = Column(Integer, ForeignKey('passengers.id'), nullable=False)
    entry_time = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    exit_time = Column(DateTime)
    status = Column(String(50), default='active')  # e.g., 'active', 'exited'
    passenger = relationship("Passenger", back_populates="lounge_entries")

    def __repr__(self):
        return f'<LoungeEntry {self.id} for Passenger {self.passenger_id}>'

class Reservation(Base):
    __tablename__ = 'reservations'
    id = Column(Integer, primary_key=True)
    passenger_name = Column(String(100), nullable=False)
    flight_number = Column(String(50))
    reservation_date = Column(Date, nullable=False)
    reservation_time = Column(Time, nullable=False)
    number_of_guests = Column(Integer, default=1)
    status = Column(String(50), default='confirmed')  # e.g., 'confirmed', 'cancelled', 'completed'

    def __repr__(self):
        return f'<Reservation {self.id} for {self.passenger_name}>'

class LoungeSetting(Base): # Renamed from LoungeSettings to singular to follow convention
    __tablename__ = 'lounge_settings'
    id = Column(Integer, primary_key=True)
    lounge_name = Column(String(100), default='Prima Vista Lounge')
    lounge_address = Column(String(200))
    lounge_capacity = Column(Integer)
    entry_tracking_method = Column(String(50)) # e.g., 'manual', 'qr_scan'

    def __repr__(self):
        return f'<LoungeSetting {self.lounge_name}>'
