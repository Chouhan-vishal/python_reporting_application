def kpi_dashboard_queries(user):

    full_name = user.full_name
    main_query = f"""
    WITH SalesTeamCTE AS (
        SELECT   
            ST.[Team Name],   
            [Sales Person], 
            CAST(GETDATE() AS DATE) AS [Date],
            CAST(0 AS DECIMAL(10, 2)) AS [Target Qty],  
            CAST(0 AS DECIMAL(10, 2)) AS [Achv Qty]
        FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
    ),
    TargetCustomers AS (
        SELECT DISTINCT  
            SV.[Team Name],    
            [Sales Person],
            ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10, 2))), 2) AS [Target Qty], 
            SV.[Date],
            COUNT(DISTINCT SV.[Customer ID]) AS [Target Customer Count]
        FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)
        WHERE [Item Category] <> 'Welding Electrodes'
        GROUP BY 
            SV.[Team Name],
            [Sales Person],
            SV.[Date]
    ),
    Sales AS (
        SELECT      
            ST.[Team Name],   
            ST.[Sales Person],
            SUM(SV.[Qty(MTs)]) AS [Achv Qty]
        FROM SalesTeamCTE ST
        INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
            AND SV.[Item Details] <> 'Welding Electrodes'
            AND SV.[Voucher Date] BETWEEN DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) AND EOMONTH(GETDATE())
        GROUP BY 
            ST.[Team Name],    
            ST.[Sales Person]
    ),
    CustomerReached AS (
        SELECT      
            TC.[Team Name],
            TC.[Sales Person],
            COUNT(DISTINCT SV.[Customer ID]) AS [Target Customer Reached]
        FROM [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_TargetCustomers] TC WITH (NOLOCK)
            ON SV.[Customer ID] = TC.[Customer ID]
        WHERE SV.[Item Details] <> 'Welding Electrodes'
        AND SV.[Voucher Date] BETWEEN DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1) AND EOMONTH(GETDATE())
        GROUP BY 
            TC.[Team Name], TC.[Sales Person]
    ),
    Outstanding AS (
        SELECT  
            ST.[Team Name],
            OS.[Sales Person -2] AS [Sales Person],
            SUM(OS.[Pending Amount]) AS [Total Outstanding]
        FROM [dbo].[tbl_OutStandings] OS WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
            ON LTRIM(RTRIM(OS.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        WHERE 
            CAST(OS.[Created Date] AS DATE) = DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
        GROUP BY 
            ST.[Team Name],
            OS.[Sales Person -2]
    ),
    SalesPersonAmount AS (
        SELECT
            ST.[Team Name],
            ST.[Sales Person],
            SUM(SV.Amount * 1.18) AS [Sales Person -2 Amount]
        FROM [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
            ON SV.[Sales Person -2] = ST.[Sales Person]
        WHERE MONTH(SV.[Voucher Date]) = 5
        AND YEAR(SV.[Voucher Date]) = YEAR(GETDATE())
        GROUP BY 
            ST.[Team Name], ST.[Sales Person]
    )
    SELECT DISTINCT 
        ST.[Team Name],
        ST.[Sales Person],
        ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS [Target Qty],  
        ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS [Achv Qty],
        ISNULL((SELECT [Target Customer Count] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS [Target Customer Count],
        ISNULL((SELECT [Target Customer Reached] FROM CustomerReached WHERE CustomerReached.[Team Name] = ST.[Team Name] AND CustomerReached.[Sales Person] = ST.[Sales Person]), 0) AS [Target Customer Reached],
        ISNULL(ROUND(CAST(ISNULL((SELECT [Target Customer Reached] FROM CustomerReached WHERE CustomerReached.[Team Name] = ST.[Team Name] AND CustomerReached.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT) / NULLIF(CAST(ISNULL((SELECT [Target Customer Count] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT), 0) * 100, 0), 2) AS [Reached %],
        ISNULL((SELECT [Total Outstanding] FROM Outstanding WHERE Outstanding.[Team Name] = ST.[Team Name] AND Outstanding.[Sales Person] = ST.[Sales Person]), 0) AS [Total Outstanding],
        ISNULL((SELECT [Sales Person -2 Amount] FROM SalesPersonAmount WHERE SalesPersonAmount.[Team Name] = ST.[Team Name] AND SalesPersonAmount.[Sales Person] = ST.[Sales Person]), 0) AS [Sales Person -2 Amount],
        ISNULL((SELECT ([Total Outstanding] / NULLIF((SELECT [Sales Person -2 Amount] FROM SalesPersonAmount WHERE SalesPersonAmount.[Team Name] = ST.[Team Name] AND SalesPersonAmount.[Sales Person] = ST.[Sales Person]), 0)) * 31 FROM Outstanding WHERE Outstanding.[Team Name] = ST.[Team Name] AND Outstanding.[Sales Person] = ST.[Sales Person]), 0) AS [Average Payment Days]
    FROM SalesTeamCTE ST
    WHERE LOWER(ST.[Sales Person]) = LOWER('{full_name}')
    ORDER BY ST.[Team Name], ST.[Sales Person];

    """

    customers_query = f"""
    SELECT
        [Customer Type],
        COUNT(*) AS NewCustomersCreated
    FROM tbl_CustomerList
    WHERE 
        MONTH([Date of Creation]) = MONTH(GETDATE())  -- Filter by current month
        AND YEAR([Date of Creation]) = YEAR(GETDATE()) -- Filter by current year
        AND LOWER([Sales Person]) = LOWER('{full_name}')
    GROUP BY [Customer Type];
    """
    return main_query, customers_query
