"""
generate_dataset.py: Generates a complete 1,200+ record high-frequency CAN-bus
and telematics time-series dataset along the Madurai -> Chennai (NH 45) corridor.
"""

import math
import random
import datetime
import pandas as pd

WAYPOINTS = [
    (9.9325, 78.1633, "Madurai Mattuthavani Freight Terminal"),
    (10.0336, 78.3370, "Melur Toll Plaza"),
    (10.3673, 78.4800, "Thuvarankurichi Waypoint"),
    (10.6033, 78.5436, "Viralimalai Industrial Zone"),
    (10.7905, 78.7047, "Tiruchirappalli (Trichy) Bypass Hub"),
    (10.9238, 78.7397, "Samayapuram Expressway Gate"),
    (11.2335, 78.8817, "Perambalur Freight Stop"),
    (11.6917, 79.2900, "Ulundurpet NH 45 Junction"),
    (11.9401, 79.4861, "Villupuram Bypass Depot"),
    (12.2333, 79.6500, "Tindivanam Logistics Hub"),
    (12.4333, 79.8333, "Melmaruvathur Waypoint"),
    (12.6819, 79.9888, "Chengalpattu Toll Plaza"),
    (12.9249, 80.1000, "Tambaram Southern Freight Gateway"),
    (13.0827, 80.2707, "Chennai Madhavaram Central Freight Complex")
]

TOTAL_KM = 462.0
TOTAL_RECORDS = 1250

def generate_telematics_data():
    records = []
    base_time = datetime.datetime.now() - datetime.timedelta(seconds=TOTAL_RECORDS * 2)
    
    # Corridor waypoint interpolation helper
    n_segments = len(WAYPOINTS) - 1
    
    current_speed = 0.0
    
    for i in range(TOTAL_RECORDS):
        ts = (base_time + datetime.timedelta(seconds=i * 2)).strftime("%Y-%m-%d %H:%M:%S")
        progress_ratio = i / (TOTAL_RECORDS - 1)
        dist_covered = round(progress_ratio * TOTAL_KM, 2)
        
        # Segment calculation
        seg_idx = min(n_segments - 1, int(progress_ratio * n_segments))
        seg_t = (progress_ratio * n_segments) - seg_idx
        p1 = WAYPOINTS[seg_idx]
        p2 = WAYPOINTS[seg_idx + 1]
        
        lat = round(p1[0] + (p2[0] - p1[0]) * seg_t, 5)
        lon = round(p1[1] + (p2[1] - p1[1]) * seg_t, 5)
        
        dy = p2[0] - p1[0]
        dx = (p2[1] - p1[1]) * math.cos(math.radians(p1[0]))
        heading = round((math.degrees(math.atan2(dx, dy)) + 360) % 360, 1)
        
        # Realistic driving profiles:
        # Phase 1: 0 - 30: Departure & slow acceleration
        # Phase 2: 31 - 420: Highway cruising at 68-76 km/h
        # Phase 3: 421 - 465: Fatigue/microsleep episode (EAR drops, speed stays 78-85 km/h)
        # Phase 4: 466 - 480: Hard brake event (-16 km/h/s) and recovery
        # Phase 5: 481 - 850: Stable highway transit (65-74 km/h)
        # Phase 6: 851 - 890: Yawning fatigue episode (MAR spikes to 0.75, speed 70 km/h)
        # Phase 7: 891 - 1209: Highway cruising approaching Chennai
        # Phase 8: 1210 - 1250: Arrival & safe deceleration to 0 km/h
        
        if i < 30:
            target_speed = min(45.0, i * 1.5)
            gear = min(4, max(1, int(target_speed // 10) + 1))
            rpm = int(1100 + target_speed * 18)
            throttle = min(60.0, target_speed * 1.4)
            brake = 0.0
            ear = round(random.uniform(0.29, 0.35), 2)
            mar = round(random.uniform(0.18, 0.26), 2)
            fatigue = round(random.uniform(5.0, 15.0), 1)
            status = "NOMINAL"
        elif 420 <= i <= 465:
            # Microsleep hazard scenario
            target_speed = 78.0 + random.uniform(0, 4)
            gear = 7
            rpm = 1550
            throttle = 45.0
            brake = 0.0
            ear = round(random.uniform(0.10, 0.16), 2) # Eye closure
            mar = round(random.uniform(0.20, 0.28), 2)
            fatigue = round(random.uniform(75.0, 92.0), 1)
            status = "CRITICAL"
        elif 466 <= i <= 475:
            # Sudden hard brake post-alarm
            target_speed = max(25.0, current_speed - 18.0)
            gear = 4
            rpm = 1200
            throttle = 0.0
            brake = 85.0
            ear = round(random.uniform(0.25, 0.32), 2) # Eyes snap open
            mar = round(random.uniform(0.22, 0.30), 2)
            fatigue = round(random.uniform(55.0, 68.0), 1)
            status = "WARNING"
        elif 850 <= i <= 890:
            # Repeated yawning episode
            target_speed = 68.0 + random.uniform(-2, 2)
            gear = 7
            rpm = 1450
            throttle = 40.0
            brake = 0.0
            ear = round(random.uniform(0.22, 0.28), 2)
            mar = round(random.uniform(0.65, 0.82), 2) # Wide mouth open (yawn)
            fatigue = round(random.uniform(65.0, 78.0), 1)
            status = "WARNING"
        elif i >= 1210:
            # Final approach & safe stop
            decay_factor = (1250 - i) / 40.0
            target_speed = max(0.0, 50.0 * max(0.0, decay_factor))
            if target_speed < 2.0:
                target_speed = 0.0
            gear = 1 if target_speed > 0 else 0
            rpm = int(800 + target_speed * 12) if target_speed > 0 else 650
            throttle = 0.0
            brake = 35.0 if target_speed > 0 else 0.0
            ear = round(random.uniform(0.28, 0.34), 2)
            mar = round(random.uniform(0.18, 0.25), 2)
            fatigue = round(random.uniform(10.0, 20.0), 1)
            status = "SAFE_STOP" if target_speed == 0.0 else "NOMINAL"
        else:
            # Nominal high-speed cruising
            target_speed = 70.0 + random.uniform(-3, 4)
            gear = 7
            rpm = int(1400 + (target_speed - 70) * 25)
            throttle = round(random.uniform(35.0, 48.0), 1)
            brake = 0.0
            ear = round(random.uniform(0.28, 0.35), 2)
            mar = round(random.uniform(0.18, 0.27), 2)
            fatigue = round(random.uniform(8.0, 22.0), 1)
            status = "NOMINAL"

        # Calculate instantaneous acceleration
        accel = round((target_speed - current_speed) / 2.0, 2)
        current_speed = round(target_speed, 1)

        records.append({
            "timestamp": ts,
            "vehicle_id": "TN 58 AA 4920",
            "driver_name": "Arun Kumar (Operator #104)",
            "speed_kmh": current_speed,
            "acceleration_kmh_s": accel,
            "latitude": lat,
            "longitude": lon,
            "heading_deg": heading,
            "throttle_pct": throttle,
            "brake_pct": brake,
            "rpm": rpm,
            "gear": gear,
            "engine_temp_c": round(86.0 + (current_speed / 100.0) * 6.0 + random.uniform(-0.5, 0.5), 1),
            "ear": ear,
            "mar": mar,
            "fatigue_score": fatigue,
            "status": status
        })

    df = pd.DataFrame(records)
    return df

if __name__ == "__main__":
    df = generate_telematics_data()
    df.to_csv("telematics.csv", index=False)
    print(f"[+] Successfully generated telematics.csv with {len(df)} records.")
    print(f"    Speed: Min={df['speed_kmh'].min():.1f}, Max={df['speed_kmh'].max():.1f}, Avg={df['speed_kmh'].mean():.1f} km/h")
    print(f"    Waypoints: Lat {df['latitude'].min()} - {df['latitude'].max()}, Lon {df['longitude'].min()} - {df['longitude'].max()}")
