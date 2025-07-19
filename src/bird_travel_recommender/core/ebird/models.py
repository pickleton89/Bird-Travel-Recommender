"""
Pydantic response models for eBird API data.

This module provides type-safe data models that eliminate the need
for duplicate response handling in sync and async clients.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Union
from datetime import datetime


class TaxonomyModel(BaseModel):
    """eBird taxonomy entry model."""
    
    species_code: str = Field(..., description="Unique species code")
    common_name: str = Field(..., description="Common species name")
    scientific_name: str = Field(..., description="Scientific species name")
    category: str = Field(..., description="Species category")
    order: str = Field(..., description="Taxonomic order")
    family: str = Field(..., description="Taxonomic family")
    com_name_codes: Optional[List[str]] = Field(None, description="Common name codes")
    sci_name_codes: Optional[List[str]] = Field(None, description="Scientific name codes")
    band_codes: Optional[List[str]] = Field(None, description="Banding codes")
    
    @validator("species_code")
    def validate_species_code(cls, v):
        """Ensure species code is not empty."""
        if not v or not v.strip():
            raise ValueError("Species code cannot be empty")
        return v.strip()


class ObservationModel(BaseModel):
    """eBird observation model."""
    
    species_code: str = Field(..., description="Species code")
    common_name: str = Field(..., description="Common species name")
    scientific_name: str = Field(..., description="Scientific species name")
    location_id: str = Field(..., description="Location identifier")
    location_name: str = Field(..., description="Location name")
    observation_date: str = Field(..., description="Observation date")
    how_many: Optional[int] = Field(None, description="Number observed")
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")
    obs_valid: Optional[bool] = Field(None, description="Observation validity")
    obs_reviewed: Optional[bool] = Field(None, description="Observation reviewed")
    location_private: Optional[bool] = Field(None, description="Private location")
    sub_id: Optional[str] = Field(None, description="Submission ID")
    
    @validator("lat")
    def validate_latitude(cls, v):
        """Validate latitude range."""
        if v < -90 or v > 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v
        
    @validator("lng")
    def validate_longitude(cls, v):
        """Validate longitude range."""
        if v < -180 or v > 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v


class LocationModel(BaseModel):
    """eBird location model."""
    
    location_id: str = Field(..., description="Location identifier")
    name: str = Field(..., description="Location name")
    latitude: float = Field(..., description="Latitude")
    longitude: float = Field(..., description="Longitude")
    country_code: str = Field(..., description="Country code")
    country_name: str = Field(..., description="Country name")
    subnational1_code: Optional[str] = Field(None, description="State/province code")
    subnational1_name: Optional[str] = Field(None, description="State/province name")
    subnational2_code: Optional[str] = Field(None, description="County code")
    subnational2_name: Optional[str] = Field(None, description="County name")
    is_hotspot: Optional[bool] = Field(None, description="Is location a hotspot")
    hierarchical_name: Optional[str] = Field(None, description="Hierarchical name")


class RegionModel(BaseModel):
    """eBird region model."""
    
    code: str = Field(..., description="Region code")
    name: str = Field(..., description="Region name")
    
    
class ChecklistModel(BaseModel):
    """eBird checklist model."""
    
    checklist_id: str = Field(..., description="Checklist identifier", alias="subId")
    user_display_name: str = Field(..., description="Observer name", alias="userDisplayName")
    obs_date: str = Field(..., description="Observation date", alias="obsDt")
    location_id: str = Field(..., description="Location identifier", alias="locId")
    location_name: str = Field(..., description="Location name", alias="locName")
    num_species: Optional[int] = Field(None, description="Number of species", alias="numSpecies")
    all_obs_reported: Optional[bool] = Field(None, description="All observations reported", alias="allObsReported")
    
    class Config:
        allow_population_by_field_name = True


class FrequencyModel(BaseModel):
    """eBird frequency model."""
    
    month_qt: str = Field(..., description="Month and week")
    frequency: float = Field(..., description="Frequency value")
    sample_size: int = Field(..., description="Sample size", alias="sampleSize")
    
    @validator("frequency")
    def validate_frequency(cls, v):
        """Validate frequency is between 0 and 1."""
        if v < 0 or v > 1:
            raise ValueError("Frequency must be between 0 and 1")
        return v
        
    class Config:
        allow_population_by_field_name = True


class HotspotModel(BaseModel):
    """eBird hotspot model."""
    
    location_id: str = Field(..., description="Hotspot identifier", alias="locId")
    location_name: str = Field(..., description="Hotspot name", alias="locName")
    country_code: str = Field(..., description="Country code", alias="countryCode")
    subnational1_code: str = Field(..., description="State/province code", alias="subnational1Code")
    latitude: float = Field(..., description="Latitude", alias="lat")
    longitude: float = Field(..., description="Longitude", alias="lng")
    latest_obs_date: Optional[str] = Field(None, description="Latest observation date", alias="latestObsDt")
    num_species_all_time: Optional[int] = Field(None, description="All-time species count", alias="numSpeciesAllTime")
    
    class Config:
        allow_population_by_field_name = True