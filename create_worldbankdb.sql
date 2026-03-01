IF DB_ID('WorldBankDB') IS NOT NULL
BEGIN
	USE WorldBankDB;
END

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Countries')
BEGIN
	CREATE TABLE Countries (
		country_id INT IDENTITY(1,1) PRIMARY KEY,
		name NVARCHAR(200) NOT NULL UNIQUE
	);
END

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Years')
BEGIN
	CREATE TABLE Years (
		year INT PRIMARY KEY
	);
END

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'Observations')
BEGIN
	CREATE TABLE Observations (
		obs_id INT IDENTITY(1,1) PRIMARY KEY,
		country_id INT NOT NULL,
		year INT NOT NULL,
		gdp_usd DECIMAL(20,2) NULL,
		population BIGINT NULL,
		life_expectancy DECIMAL(6,2) NULL,
		unemployment_rate_pct DECIMAL(6,2) NULL,
		co2_tons_per_capita DECIMAL(6,2) NULL,
		access_to_electricity_pct DECIMAL(6,2) NULL,
		CONSTRAINT FK_Obs_Country FOREIGN KEY (country_id) REFERENCES Countries(country_id),
		CONSTRAINT FK_Obs_Year FOREIGN KEY (year) REFERENCES Years(year),
		CONSTRAINT UQ_Observations_Country_Year UNIQUE (country_id, year)
	);
END

-- End of SQL Server section

