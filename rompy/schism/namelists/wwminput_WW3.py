from pydantic import Field

from rompy.schism.namelists.basemodel import NamelistBaseModel


class PROC(NamelistBaseModel):
    PROCNAME: str = Field("'Isabel'", description="Project Name")
    DIMMODE: int = Field(
        2,
        description="Mode of run (ex: 1 = 1D, 2 = 2D) always 2D when coupled to SCHISM",
    )
    LSTEA: str = Field("F", description="steady mode; under development")
    LQSTEA: str = Field(
        "F",
        description="Quasi-Steady Mode; In this case WWM-II is doing subiterations defined as DELTC/NQSITER unless QSCONVI is not reached",
    )
    LSPHE: str = Field("T", description="Spherical coordinates (lon/lat)")
    LNAUTIN: str = Field(
        "T",
        description="Nautical convention for all inputs given in degrees (suggestion: T)",
    )
    LNAUTOUT: str = Field("T", description="Output in Nautical convention")
    LMONO_IN: str = Field(
        "F",
        description="For prescribing monochromatic wave height Hmono as a boundary conditions; incident wave is defined as monochromatic wave height, which is Hmono = sqrt(2) * Hs",
    )
    LMONO_OUT: str = Field("F", description="Output wave heights in terms of Lmono")
    BEGTC: str = Field(
        "'20030908.000000'",
        description="Time for start the simulation, ex:yyyymmdd. hhmmss",
    )
    DELTC: int = Field(
        600, description="Time step (MUST match dt*nstep_wwm in SCHISM!)"
    )
    UNITC: str = Field("'SEC'", description="Unity of time step")
    ENDTC: str = Field(
        "'20031008.000000'",
        description="Time for stop the simulation, ex:yyyymmdd. hhmmss",
    )
    DMIN: float = Field(
        0.01, description="Minimum water depth. This must be the same as h0 in SCHISM"
    )


class COUPL(NamelistBaseModel):
    LCPL: str = Field(
        "T",
        description="Couple with current model ... main switch - keep it on for SCHISM-WWM",
    )
    RADFLAG: str = Field(
        "'LON'", description="LON: Longuet-Higgin; VOR: vortex formulation"
    )
    LETOT: str = Field(
        "F",
        description="Option to compute the wave induced radiation stress. If .T. the radiation stress is based on the integrated wave spectrum",
    )
    NLVT: int = Field(10, description="Number of vertical Layers; not used with SCHISM")
    DTCOUP: float = Field(
        600.0, description="Couple time step - not used when coupled to SCHISM"
    )


class GRID(NamelistBaseModel):
    LCIRD: str = Field("T", description="Full circle in directional space")
    LSTAG: str = Field(
        "F",
        description="Stagger directional bins with a half Dtheta; may use T only for regular grid to avoid char. line aligning with grid line",
    )
    MINDIR: float = Field(
        0.0,
        description="Minimum direction for simulation (unit: degrees; nautical convention; 0: from N; 90: from E); not used if LCIRD = .T.",
    )
    MAXDIR: float = Field(
        360.0,
        description="Maximum direction for simulation (unit: degrees); may be < MINDIR; not used if LCIRD = .T.",
    )
    MDC: int = Field(36, description="Number of directional bins")
    FRLOW: float = Field(
        0.04,
        description="Low frequency limit of the discrete wave period (Hz; 1/period)",
    )
    FRHIGH: float = Field(
        1.0, description="High frequency limit of the discrete wave period."
    )
    MSC: int = Field(36, description="Number of frequency bins")
    FILEGRID: str = Field(
        "'hgrid_WWM.gr3'",
        description="Name of the grid file. hgridi_WWM.gr3 if IGRIDTYPE = 3 (SCHISM)",
    )
    IGRIDTYPE: int = Field(3, description="Gridtype used.")
    LSLOP: str = Field("F", description="Bottom Slope limiter (default=F)")
    SLMAX: float = Field(0.2, description="Max Slope;")
    LVAR1D: str = Field(
        "F", description="For 1d-mode if variable dx is used; not used with SCHISM"
    )
    LOPTSIG: str = Field(
        "F",
        description="Use optimal distributions of freq. in spectral space ... fi+1 = fi * 1.1. Take care what you high freq. limit is!",
    )


class INIT(NamelistBaseModel):
    FILEHOT_IN: str = Field(
        "'hotfile_in_WWM.nc'",
        description="(Full) hot file name for input (which can be copied from FILEHOT_OUT above)",
    )
    HOTSTYLE_IN: int = Field(2, description="1: binary hotfile of data as input")
    IHOTPOS_IN: int = Field(1, description="Position in hotfile (only for netcdf)")
    MULTIPLEIN: int = Field(0, description="0: read hotfile from one single file")


class HOTFILE(NamelistBaseModel):
    LHOTF: str = Field("T", description="Write hotfile")
    FILEHOT_OUT: str = Field("'hotfile_out_WWM.nc'", description="name of output")
    BEGTC: str = Field(
        "'20030908.000000'",
        description="Starting time of hotfile writing. With ihot!=0 in SCHISM,",
    )
    DELTC: float = Field(86400.0, description="time between hotfile writes")
    UNITC: str = Field("'SEC'", description="unit used above")
    ENDTC: str = Field(
        "'20031008.000000'",
        description="Ending time of hotfile writing (adjust with BEGTC)",
    )
    LCYCLEHOT: str = Field("T", description="Applies only to netcdf")
    HOTSTYLE_OUT: int = Field(2, description="1: binary hotfile of data as output")
    MULTIPLEOUT: int = Field(
        0, description="0: hotfile in a single file (binary or netcdf)"
    )


class BOUC(NamelistBaseModel):
    LBCSE: str = Field("T", description="The wave boundary data is time dependent")
    LBINTER: str = Field(
        "T",
        description="Do interpolation in time if LBCSE=T (not available for quasi-steady mode within the subtime steps)",
    )
    LBCWA: str = Field("T", description="Parametric Wave Spectra")
    LBCSP: str = Field(
        "F",
        description="Specify (non-parametric) wave spectra, specified in 'FILEWAVE' below",
    )
    LINHOM: str = Field("T", description="Non-uniform wave b.c. in space")
    LBSP1D: str = Field(
        "F",
        description="1D (freq. space only) format for FILEWAVE if LBCSP=T and LINHOM=F",
    )
    LBSP2D: str = Field(
        "F", description="2D format for FILEWAVE if LBCSP=T and LINHOM=F"
    )
    BEGTC: str = Field(
        "'20030908.000000'",
        description="Begin time of the wave boundary file (FILEWAVE)",
    )
    DELTC: int = Field(1, description="Time step in FILEWAVE")
    UNITC: str = Field("'HR'", description="Unit can be HR, MIN, SEC")
    ENDTC: str = Field("'20031008.000000'", description="End time")
    FILEBOUND: str = Field(
        "'wwmbnd.gr3'",
        description="Boundary file defining boundary conditions and Neumann nodes.",
    )
    IBOUNDFORMAT: int = Field(
        3, description="1 ~ WWM, 3 ~ WW3 (2D spectra in netcdf format only - LBCWA=T)."
    )
    FILEWAVE: str = Field(
        "'bndfiles.dat'", description="Boundary file defining boundary input from WW3"
    )
    LINDSPRDEG: str = Field(
        "F",
        description="If 1-d wave spectra are read this flag defines whether the input for the directional spreading is in degrees (true) or exponent (false)",
    )
    LPARMDIR: str = Field(
        "F",
        description="If LPARMDIR is true then directional spreading is read from WBDS and must be in exponential format at this time, only valid for 1d Spectra",
    )
    WBHS: float = Field(2.0, description="Hs at the boundary for parametric spectra")
    WBSS: int = Field(
        2,
        description="1 or -1: Pierson-Moskowitz, 2 or -2: JONSWAP, 3 or -3: all in one BIN,",
    )
    WBTP: float = Field(
        8.0,
        description="Tp at the boundary (sec); mean or peak depending on the sign of WBSS",
    )
    WBDM: float = Field(90.0, description="Avg. Wave Direction at the boundary")
    WBDSMS: int = Field(
        1, description="Directional spreading value in degrees (1) or as exponent (2)"
    )
    WBDS: float = Field(
        10.0, description="Directional spreading at the boundary (degrees/exponent)"
    )
    WBGAUSS: float = Field(
        0.1, description="factor for gaussian distribution if WBSS=1"
    )
    WBPKEN: float = Field(
        3.3, description="Peak enhancement factor for Jonswap Spectra if WBSS=2"
    )


class ENGS(NamelistBaseModel):
    MESNL: int = Field(
        1,
        description="Nonlinear Interaction NL4 , 1 ~ on, 0 ~ off (Discrete Interaction approx.)",
    )
    MESIN: int = Field(
        1, description="Wind input: Ardhuin et al. (1) (use LSOURCESWAM = F);"
    )
    IFRIC: int = Field(
        1,
        description="Formulation for atmospheric boundary layer, (IFRIC = 1 for MESIN = 1, IFRIC = 4 for MESIN=3);",
    )
    MESBF: int = Field(
        1,
        description="Bottom friction: 1 - JONSWAP (Default); 2 - Madsen et al. (1989); 3 - SHOWEX",
    )
    FRICC: float = Field(
        0.067,
        description="if MESBF=1: JONSWAP bottom friction coefficient [0.038,0.067]. If MESBF=2: physical bottom roughness (ignored if given in rough.gr3). If MESBF=3: D50 (if negative read from SHOWEX_D50.gr3)",
    )
    MESBR: int = Field(1, description="Shallow water wave breaking; 0: off; 1: on")
    IBREAK: int = Field(
        1, description="Wave breaking formulation: 1 - Battjes and Janssen (1978)"
    )
    ICRIT: int = Field(
        1,
        description="Wave breaking criterion: 1   - Constant breaker index (gamma) or gamma_TG defined with BRCR",
    )
    BRCR: float = Field(
        0.78,
        description="either gamma, default is 0.73 for IBREAK=1,5 or gamma_TG, default is 0.42 for IBREAK=2,3 or biphase_ref, default is -4pi/9 = -1.3963 for IBREAK=4",
    )
    a_BRCR: float = Field(0.76, description="cf ICRIT = 4, 5")
    b_BRCR: float = Field(0.29, description="cf ICRIT = 4, 5")
    min_BRCR: float = Field(0.25, description="cf ICRIT = 4, 5")
    max_BRCR: float = Field(0.8, description="cf ICRIT = 4, 5")
    a_BIPH: float = Field(
        0.2, description="Biphase coefficient, default 0.2 (intended for IBREAK=3)"
    )
    BR_COEF_METHOD: int = Field(
        1, description="Method for the breaking coefficient: 1 - constant, 2 - adaptive"
    )
    B_ALP: float = Field(
        0.5, description="breaking coefficient. If BR_COEF_METHOD = 2, B_ALP ~ 40"
    )
    ZPROF_BREAK: int = Field(
        2,
        description="Vertical distribution function of wave breaking source term, only used in 3D run",
    )
    BC_BREAK: int = Field(
        1, description="Apply depth-limited breaking at the boundaries: 1 - On; 0 - Off"
    )
    IROLLER: int = Field(
        0,
        description="Wave roller model (e.g., see Uchiyama et al., 2010): 1 - On; 0 - Off; not used at the moment",
    )
    ALPROL: float = Field(
        0.85,
        description="Alpha coefficient for the wave roller model (between 0 and 1): 1 - full conversion; 0 - no energy transferred to the roller",
    )
    MEVEG: int = Field(
        0, description="Vegetation on/off. If on, isav must = 1 in param.nml"
    )
    LMAXETOT: str = Field(
        "T",
        description="Limit shallow water wave height by wave breaking limiter (default=T)",
    )
    MESDS: int = Field(
        1,
        description="Formulation for the whitecapping source function; same value as MESIN",
    )
    MESTR: int = Field(
        1,
        description="Formulation for the triad 3 wave interactions (MESTR = 0 (off), MESTR = 1 (Lumped Triad Approx. (LTA)), MESTR = 2 (corrected version of LTA by Salmon et al. (2016)))",
    )
    TRICO: float = Field(
        0.1, description="proportionality const. (\alpha_EB); default is 0.1"
    )
    TRIRA: float = Field(
        2.5,
        description="ratio of max. freq. considered in triads over mean freq.; 2.5 is suggested",
    )
    TRIURS: float = Field(
        0.1,
        description="critical Ursell number; if Ursell # < TRIURS; triads are not computed",
    )


class NUMS(NamelistBaseModel):
    ICOMP: int = Field(3, description="")
    AMETHOD: int = Field(7, description="")
    SMETHOD: int = Field(1, description="")
    DMETHOD: int = Field(2, description="")
    RTHETA: float = Field(
        0.5,
        description="Weighing factor for DMETHOD = 1, not really useful since Crank Nicholson integration can only be monotone for CFL .le. 2",
    )
    LITERSPLIT: str = Field(
        "F",
        description="T: double Strang split; F: simple split (more efficient). Default: F",
    )
    LFILTERTH: str = Field("F", description="")
    MAXCFLTH: float = Field(
        1.0, description="Max Cfl in Theta space; used only if LFILTERTH=T"
    )
    FMETHOD: int = Field(1, description="")
    LFILTERSIG: str = Field(
        "F", description="Limit the advection velocity in freq. space (usually F)"
    )
    MAXCFLSIG: float = Field(
        1.0, description="Max Cfl in freq. space; used only if LFILTERSIG=T"
    )
    LLIMT: str = Field(
        "T",
        description="Switch on/off Action limiter, Action limiter must mostly be turned on.",
    )
    MELIM: int = Field(1, description="Formulation for the action limiter")
    LIMFAK: float = Field(
        0.1,
        description="Proportionality coefficient for the action limiter MAX_DAC_DT = Limfak * Limiter; see notes above for value",
    )
    LDIFR: str = Field(
        "F",
        description="Use phase decoupled diffraction approximation according to Holthuijsen et al. (2003) (usually T; if crash, use F)",
    )
    IDIFFR: int = Field(
        1,
        description="Extended WAE accounting for higher order effects WAE becomes nonlinear; 1: Holthuijsen et al. ; 2: Liau et al. ; 3: Toledo et al. (in preparation)",
    )
    LCONV: str = Field(
        "F",
        description="Estimate convergence criterian and write disk (quasi-steady - qstea.out)",
    )
    LCFL: str = Field("F", description="Write out CFL numbers; use F to save time")
    NQSITER: int = Field(
        1,
        description="# of quasi-steady (Q-S) sub-divisions within each WWM time step (trial and errors)",
    )
    QSCONV1: float = Field(
        0.98,
        description="Number of grid points [%/100] that have to fulfill abs. wave height criteria EPSH1",
    )
    QSCONV2: float = Field(
        0.98,
        description="Number of grid points [%/100] that have to fulfill rel. wave height criteria EPSH2",
    )
    QSCONV3: float = Field(
        0.98,
        description="Number of grid points [%/100] that have to fulfill sum. rel. wave action criteria EPSH3",
    )
    QSCONV4: float = Field(
        0.98,
        description="Number of grid points [%/100] that have to fulfill rel. avg. wave steepness criteria EPSH4",
    )
    QSCONV5: float = Field(
        0.98,
        description="Number of grid points [%/100] that have to fulfill avg. rel. wave period criteria EPSH5",
    )
    LEXPIMP: str = Field(
        "F",
        description="Use implicit schemes for freq. lower than given below by FREQEXP; used only if ICOMP=0",
    )
    FREQEXP: float = Field(
        0.1,
        description="Minimum frequency for explicit schemes; only used if LEXPIMP=T and ICOMP=0",
    )
    EPSH1: float = Field(
        0.01,
        description="Convergence criteria for rel. wave height ! EPSH1 < CONVK1 = REAL(ABS(HSOLD(IP)-HS2)/HS2)",
    )
    EPSH2: float = Field(
        0.01,
        description="Convergence criteria for abs. wave height ! EPSH2 < CONVK2 = REAL(ABS(HS2-HSOLD(IP)))",
    )
    EPSH3: float = Field(
        0.01,
        description="Convergence criteria for the rel. sum of wave action ! EPSH3 < CONVK3 = REAL(ABS(SUMACOLD(IP)-SUMAC)/SUMAC)",
    )
    EPSH4: float = Field(
        0.01,
        description="Convergence criteria for the rel. avg. wave steepness criteria ! EPSH4 < CONVK4 = REAL(ABS(KHS2-KHSOLD(IP))/KHSOLD(IP))",
    )
    EPSH5: float = Field(
        0.01,
        description="Convergence criteria for the rel. avg. waveperiod ! EPSH5 < REAL(ABS(TM02-TM02OLD(IP))/TM02OLD(IP))",
    )
    LVECTOR: str = Field(
        "F",
        description="Use optmized propagation routines for large high performance computers e.g. at least more than 128 CPU. Try LVECTOR=F first.",
    )
    IVECTOR: int = Field(
        2, description="USed if LVECTOR=T; Different flavours of communications"
    )
    LADVTEST: str = Field(
        "F",
        description="for testing the advection schemes, testcase will be added soon",
    )
    LCHKCONV: str = Field(
        "F",
        description="needs to set to .true. for quasi-steady mode. in order to compute the QSCONVi criteria and check them",
    )
    DTMIN_DYN: float = Field(
        1.0,
        description="min. time step (sec?) for dynamic integration, this controls in SMETHOD the smallest time step for the triads, DT = 1.s is found to work well.",
    )
    NDYNITER: list = Field(
        [100, ""],
        description="max. iteration for dyn. scheme afterwards the limiter is applied in the last step, for SMETHOD .eq. this controls the integration of the triad interaction terms, which is done dynamically.",
    )
    DTMIN_SIN: float = Field(
        1.0,
        description="min. time steps for the full fractional step method, where each source term is integrated with its own fractional step",
    )
    DTMIN_SNL4: float = Field(1.0, description="")
    DTMIN_SDS: float = Field(1.0, description="")
    DTMIN_SNL3: float = Field(1.0, description="")
    DTMIN_SBR: float = Field(0.1, description="")
    DTMIN_SBF: float = Field(1.0, description="")
    NDYNITER_SIN: list = Field(
        [10, ""],
        description="max. iterations for each source term in the fractional step approach.",
    )
    NDYNITER_SNL4: list = Field([10, ""], description="")
    NDYNITER_SDS: list = Field([10, ""], description="")
    NDYNITER_SBR: list = Field([10, ""], description="")
    NDYNITER_SNL3: list = Field([10, ""], description="")
    NDYNITER_SBF: list = Field([10, ""], description="")
    LSOUBOUND: str = Field(
        "F",
        description="Do source terms on boundary, this is possible as long only dissipative processes are governing the spectral evolution, otherwise, with wind u will get the max. possible wave height",
    )
    WAE_SOLVERTHR: list = Field(
        ["1.e-6", ""],
        description="Threshold for the Block-Jacobi or Block-Gauss-Seider solver",
    )
    MAXITER: list = Field([1000, ""], description="Max. number of iterations")
    PMIN: list = Field(
        [1.0, ""], description="Max. percentage of non-converged grid points"
    )
    LNANINFCHK: list = Field(
        ["F", ""],
        description="Check for NaN and INF; usually turned off for efficiency",
    )
    LZETA_SETUP: list = Field(
        ["F", ""], description="Compute wave setup (simple momentum eq.)"
    )
    ZETA_METH: list = Field(
        [0, ""], description="Method for wave setup, Mathieu please explain!"
    )
    LSOURCESWAM: list = Field(
        ["F", ""], description="Use ECMWF WAM formualtion for deep water physics."
    )
    BLOCK_GAUSS_SEIDEL: list = Field(
        ["T", ""], description="Use the Gauss Seidel on each"
    )
    LNONL: str = Field(
        "F", description="Solve the nonlinear system using simpler algorithm (Patankar)"
    )
    ASPAR_LOCAL_LEVEL: int = Field(0, description="Aspar locality level")
    L_SOLVER_NORM: str = Field(
        "F", description="Compute solver norm ||A*x-b|| as termination"
    )
    LACCEL: str = Field("F", description="")


class HISTORY(NamelistBaseModel):
    BEGTC: str = Field(
        "'20030908.000000'", description="Start output time, yyyymmdd. hhmmss;"
    )
    DELTC: int = Field(
        1,
        description="Time step for output; if smaller than simulation time step, the latter is used (output every step for better 1D 2D spectra analysis)",
    )
    UNITC: str = Field("'SEC'", description="Unit")
    ENDTC: str = Field(
        "'20031008.000000'", description="Stop time output, yyyymmdd. hhmmss"
    )
    DEFINETC: int = Field(86400, description="Time scoop (sec) for history files")
    OUTSTYLE: str = Field("'NO'", description="output option - use 'NO' for no output")
    MULTIPLEOUT: int = Field(0, description="0: output in a single netcdf file")
    USE_SINGLE_OUT: str = Field("T", description="T: Use single precision in the")
    PARAMWRITE: str = Field("T", description="T: Write the physical parametrization")
    GRIDWRITE: str = Field(
        "T", description="T/F: Write the grid in the netcdf history file (default T)"
    )
    PRINTMMA: str = Field("F", description="T/F: Print minimum, maximum and average")
    FILEOUT: str = Field("'wwm_hist.dat'", description="")
    HS: str = Field("F", description="significant wave height")
    TM01: str = Field("F", description="mean period")
    TM02: str = Field("F", description="zero-crossing mean period")
    KLM: str = Field("F", description="mean wave number")
    WLM: str = Field("F", description="mean wave length")
    ETOTC: str = Field("F", description="Variable ETOTC")
    ETOTS: str = Field("F", description="Variable ETOTS")
    DM: str = Field("F", description="mean wave direction")
    DSPR: str = Field("F", description="directional spreading")
    TPPD: str = Field("F", description="direaction of the peak ... check source code")
    TPP: str = Field("F", description="peak period")
    CPP: str = Field("F", description="peak phase vel.")
    WNPP: str = Field("F", description="peak wave number")
    CGPP: str = Field("F", description="peak group speed")
    KPP: str = Field("F", description="peak wave number")
    LPP: str = Field("F", description="peak wave length")
    PEAKD: str = Field("F", description="peak direction")
    PEAKDSPR: str = Field("F", description="peak directional spreading")
    DPEAK: str = Field("F", description="peak direction")
    UBOT: str = Field("F", description="bottom exc. vel.")
    ORBITAL: str = Field("F", description="bottom orbital vel.")
    BOTEXPER: str = Field("F", description="bottom exc.")
    TMBOT: str = Field("F", description="bottom period")
    URSELL: str = Field("F", description="Ursell number")
    UFRIC: str = Field("F", description="air friction velocity")
    Z0: str = Field("F", description="air roughness length")
    ALPHA_CH: str = Field("F", description="Charnoch coefficient for air")
    WINDX: str = Field("F", description="Wind in X direction")
    WINDY: str = Field("F", description="Wind in Y direction")
    CD: str = Field("F", description="Drag coefficient")
    CURRTX: str = Field("F", description="current in X direction")
    CURRTY: str = Field("F", description="current in Y direction")
    WATLEV: str = Field("F", description="water level")
    WATLEVOLD: str = Field("F", description="water level at previous time step")
    DEPDT: str = Field("F", description="change of water level in time")
    DEP: str = Field("F", description="depth")
    TAUW: str = Field("F", description="surface stress from the wave")
    TAUHF: str = Field("F", description="high frequency surface stress")
    TAUTOT: str = Field("F", description="total surface stress")
    STOKESSURFX: str = Field("F", description="Surface Stokes drift in X direction")
    STOKESSURFY: str = Field("F", description="Surface Stokes drift in X direction")
    STOKESBAROX: str = Field("F", description="Barotropic Stokes drift in X direction")
    STOKESBAROY: str = Field("F", description="Barotropic Stokes drift in Y direction")
    RSXX: str = Field("F", description="RSXX potential of LH")
    RSXY: str = Field("F", description="RSXY potential of LH")
    RSYY: str = Field("F", description="RSYY potential of LH")
    CFL1: str = Field("F", description="CFL number 1")
    CFL2: str = Field("F", description="CFL number 2")
    CFL3: str = Field("F", description="CFL number 3")


class STATION(NamelistBaseModel):
    BEGTC: str = Field(
        "'20030908.000000'",
        description="Start simulation time, yyyymmdd. hhmmss; must fit the simulation time otherwise no output",
    )
    DELTC: int = Field(
        600,
        description="Time step for output; if smaller than simulation time step, the latter is used (output every step for better 1D 2D spectra analysis)",
    )
    UNITC: str = Field("'SEC'", description="Unit")
    ENDTC: str = Field(
        "'20031008.000000'", description="Stop time simulation, yyyymmdd. hhmmss"
    )
    DEFINETC: int = Field(86400, description="Time for definition of station files")
    OUTSTYLE: str = Field("'NO'", description="output option")
    MULTIPLEOUT: int = Field(0, description="0: output in a single netcdf file")
    USE_SINGLE_OUT: str = Field("T", description="T: Use single precision in the")
    PARAMWRITE: str = Field("T", description="T: Write the physical parametrization")
    FILEOUT: str = Field("'wwm_sta.dat'", description="not used")
    LOUTITER: str = Field("F", description="")
    IOUTS: list = Field([15, ""], description="")
    NOUTS: list = Field(
        [
            "'P-1'",
            "'P-2'",
            "'P-3'",
            "'P-4'",
            "'P-5'",
            "'P-6'",
            "'P-7'",
            "'P-8'",
            "'P-9'",
            "'P-10'",
            "'P-11'",
            "'P-12'",
            "'P-13'",
            "'P-14'",
            "'P-15'",
        ],
        description="",
    )
    XOUTS: list = Field([-76.046, -76.778, -75.81, -75.72, -74.842, ""], description="")
    YOUTS: list = Field([39.152, 38.556, 38.033, 37.551, ""], description="")
    CUTOFF: str = Field(
        "15*0.44",
        description="cutoff freq (Hz) for each station - consistent with buoys",
    )
    LSP1D: str = Field("T", description="1D spectral station output")
    LSP2D: str = Field("F", description="2D spectral station output")
    LSIGMAX: str = Field(
        "T",
        description="Adjust the cut-freq. for the output (e.g. consistent with buoy cut-off freq.)",
    )
    AC: str = Field("F", description="spectrum")
    WK: str = Field("F", description="variable WK")
    ACOUT_1D: str = Field("F", description="variable ACOUT_1D")
    ACOUT_2D: str = Field("F", description="variable ACOUT_2D")
    HS: str = Field("F", description="significant wave height")
    TM01: str = Field("F", description="mean period")
    TM02: str = Field("F", description="zero-crossing mean period")
    KLM: str = Field("F", description="mean wave number")
    WLM: str = Field("F", description="mean wave length")
    ETOTC: str = Field("F", description="Variable ETOTC")
    ETOTS: str = Field("F", description="Variable ETOTS")
    DM: str = Field("F", description="mean wave direction")
    DSPR: str = Field("F", description="directional spreading")
    TPPD: str = Field("F", description="Discrete Peak Period")
    TPP: str = Field("F", description="Peak Period")
    CPP: str = Field("F", description="")
    WNPP: str = Field("F", description="peak wave number")
    CGPP: str = Field("F", description="peak group speed")
    KPP: str = Field("F", description="peak wave number")
    LPP: str = Field("F", description="peak")
    PEAKD: str = Field("F", description="peak direction")
    PEAKDSPR: str = Field("F", description="peak directional spreading")
    DPEAK: str = Field("F", description="")
    UBOT: str = Field("F", description="")
    ORBITAL: str = Field("F", description="")
    BOTEXPER: str = Field("F", description="")
    TMBOT: str = Field("F", description="")
    URSELL: str = Field("F", description="Ursell number")
    UFRIC: str = Field("F", description="air friction velocity")
    Z0: str = Field("F", description="air roughness length")
    ALPHA_CH: str = Field("F", description="Charnoch coefficient for air")
    WINDX: str = Field("F", description="Wind in X direction")
    WINDY: str = Field("F", description="Wind in Y direction")
    CD: str = Field("F", description="Drag coefficient")
    CURRTX: str = Field("F", description="current in X direction")
    CURRTY: str = Field("F", description="current in Y direction")
    WATLEV: str = Field("F", description="water level")
    WATLEVOLD: str = Field("F", description="water level at previous time step")
    DEPDT: str = Field("F", description="change of water level in time")
    DEP: str = Field("F", description="depth")
    TAUW: str = Field("F", description="surface stress from the wave")
    TAUHF: str = Field("F", description="high frequency surface stress")
    TAUTOT: str = Field("F", description="total surface stress")
    STOKESSURFX: str = Field("F", description="Surface Stokes drift in X direction")
    STOKESSURFY: str = Field("F", description="Surface Stokes drift in X direction")
    STOKESBAROX: str = Field("F", description="Barotropic Stokes drift in X direction")
    STOKESBAROY: str = Field("F", description="Barotropic Stokes drift in Y direction")
    RSXX: str = Field("F", description="RSXX potential of LH")
    RSXY: str = Field("F", description="RSXY potential of LH")
    RSYY: str = Field("F", description="RSYY potential of LH")
    CFL1: str = Field("F", description="CFL number 1")
    CFL2: str = Field("F", description="CFL number 2")
    CFL3: str = Field("F", description="CFL number 3")


class PETSCOPTIONS(NamelistBaseModel):
    KSPTYPE: str = Field("'LGMRES'", description="")
    RTOL: str = Field(
        "1.E-20",
        description="the relative convergence tolerance (relative decrease in the residual norm)",
    )
    ABSTOL: str = Field(
        "1.E-20",
        description="the absolute convergence tolerance (absolute size of the residual norm)",
    )
    DTOL: float = Field(10000.0, description="the divergence tolerance")
    MAXITS: int = Field(1000, description="maximum number of iterations to use")
    INITIALGUESSNONZERO: str = Field(
        "F",
        description="Tells the iterative solver that the initial guess is nonzero; otherwise KSP assumes the initial guess is to be zero",
    )
    GMRESPREALLOCATE: str = Field(
        "T",
        description="Causes GMRES and FGMRES to preallocate all its needed work vectors at initial setup rather than the default, which is to allocate them in chunks when needed.",
    )
    PCTYPE: str = Field("'SOR'", description="")


class NESTING(NamelistBaseModel):
    ListBEGTC: str = Field("''", description="")
    ListDELTC: str = Field("ZERO", description="")
    ListUNITC: str = Field("''", description="")
    ListENDTC: str = Field("''", description="")
    ListIGRIDTYPE: int = Field(0, description="")
    ListFILEGRID: str = Field("''", description="")
    ListFILEBOUND: str = Field("''", description="")
    ListPrefix: str = Field("''", description="")


class WWMINPUT(NamelistBaseModel):
    """

    This file was auto generated from a schism namelist file on 2023-11-20.
    The full contents of the namelist file are shown below providing
    associated documentation for the objects:

    ! This is the main input for WWM (based on Hurricabe Isabel for Ches Bay test)
    ! Other mandatory inputs: wwmbnd.gr3 (boundary flag files; see below)
    ! Depending on the choices of parameters below you may need additional inputs

    ! Hotstart option for WWM: see header of spectra

    &PROC
     PROCNAME       = 'Isabel'           ! Project Name
     DIMMODE        = 2                  ! Mode of run (ex: 1 = 1D, 2 = 2D) always 2D when coupled to SCHISM
     LSTEA          = F                  ! steady mode; under development
     LQSTEA         = F                  ! Quasi-Steady Mode; In this case WWM-II is doing subiterations defined as DELTC/NQSITER unless QSCONVI is not reached
     LSPHE          = T                  ! Spherical coordinates (lon/lat)
     LNAUTIN        = T                  ! Nautical convention for all inputs given in degrees (suggestion: T)
     LNAUTOUT       = T                  ! Output in Nautical convention
                                         ! If T, 0 is _from_ north, 90 is from east etc;
                                         ! If F, maths. convention - 0: to east; 90: going to north
     LMONO_IN       = F                  ! For prescribing monochromatic wave height Hmono as a boundary conditions; incident wave is defined as monochromatic wave height, which is Hmono = sqrt(2) * Hs
     LMONO_OUT      = F                  ! Output wave heights in terms of Lmono
     BEGTC          = '20030908.000000'  ! Time for start the simulation, ex:yyyymmdd. hhmmss
     DELTC          = 600                ! Time step (MUST match dt*nstep_wwm in SCHISM!)
     UNITC          = 'SEC'              ! Unity of time step
     ENDTC          = '20031008.000000'  ! Time for stop the simulation, ex:yyyymmdd. hhmmss
     DMIN           = 0.01              ! Minimum water depth. This must be the same as h0 in SCHISM
    /

    &COUPL
     LCPL           = T                  ! Couple with current model ... main switch - keep it on for SCHISM-WWM
     RADFLAG        = 'LON'              ! LON: Longuet-Higgin; VOR: vortex formulation
     LETOT          = F                  ! Option to compute the wave induced radiation stress. If .T. the radiation stress is based on the integrated wave spectrum
                                         ! e.g. Etot = Int,0,inf;Int,0,2*pi[N(sigma,theta)]dsigma,dtheta. If .F. the radiation stress is estimated as given in Roland et al. (2008) based
                                         ! on the directional spectra itself. It is always desirable to use .F., since otherwise the spectral informations are truncated and therefore
                                         ! LETOT = .T., is only for testing and developers!
     NLVT           = 10                 ! Number of vertical Layers; not used with SCHISM
     DTCOUP         = 600.               ! Couple time step - not used when coupled to SCHISM
    /

    &GRID
     LCIRD          = T                  ! Full circle in directional space
     LSTAG          = F                  ! Stagger directional bins with a half Dtheta; may use T only for regular grid to avoid char. line aligning with grid line
     MINDIR         = 0.                 ! Minimum direction for simulation (unit: degrees; nautical convention; 0: from N; 90: from E); not used if LCIRD = .T.
     MAXDIR         = 360.               ! Maximum direction for simulation (unit: degrees); may be < MINDIR; not used if LCIRD = .T.
     MDC            = 36                 ! Number of directional bins
     FRLOW          = 0.04               ! Low frequency limit of the discrete wave period (Hz; 1/period)
     FRHIGH         = 1.                 ! High frequency limit of the discrete wave period.
     MSC            = 36                 ! Number of frequency bins
     FILEGRID       = 'hgrid_WWM.gr3'    ! Name of the grid file. hgridi_WWM.gr3 if IGRIDTYPE = 3 (SCHISM)
     IGRIDTYPE      = 3                  ! Gridtype used.
                                         ! 1 ~ XFN system.dat
                                         ! 2 ~ WWM-PERIODIC
                                         ! 3 ~ SCHISM
                                         ! 4 ~ old WWM type
     LSLOP          = F                  ! Bottom Slope limiter (default=F)
     SLMAX          = 0.2                ! Max Slope;
     LVAR1D         = F                  ! For 1d-mode if variable dx is used; not used with SCHISM
     LOPTSIG        = F                  ! Use optimal distributions of freq. in spectral space ... fi+1 = fi * 1.1. Take care what you high freq. limit is!
    /

    &INIT
     LHOTR          = F                  ! Use hotstart file (see &HOTFILE section for input file)
     LINID          = T                  ! Initial condition; F for default; use T if using WW3 as i.c. etc
     INITSTYLE      = 2                  ! 1 - Parametric Jonswap, 2 - Read from Global NETCDF files, work only if IBOUNDFORMAT=3
    /

    &BOUC
     LBCSE          = T                  ! The wave boundary data is time dependent
     LBINTER        = T                  ! Do interpolation in time if LBCSE=T (not available for quasi-steady mode within the subtime steps)
     LBCWA          = T                  ! Parametric Wave Spectra
     LBCSP          = F                  ! Specify (non-parametric) wave spectra, specified in 'FILEWAVE' below
     LINHOM         = T                  ! Non-uniform wave b.c. in space
     LBSP1D         = F                  ! 1D (freq. space only) format for FILEWAVE if LBCSP=T and LINHOM=F
     LBSP2D         = F                  ! 2D format for FILEWAVE if LBCSP=T and LINHOM=F
     BEGTC          = '20030908.000000'  ! Begin time of the wave boundary file (FILEWAVE)
     DELTC          = 1                  ! Time step in FILEWAVE
     UNITC          = 'HR'               ! Unit can be HR, MIN, SEC
     ENDTC          = '20031008.000000'  ! End time
     FILEBOUND      = 'wwmbnd.gr3'       ! Boundary file defining boundary conditions and Neumann nodes.
                                         ! In this file there is following definition Flag 0: not on boundary; 3: Neumann (0 gradient only for advection part);
                                         ! 2: active bnd (Dirichlet)
     IBOUNDFORMAT   = 3                  ! 1 ~ WWM, 3 ~ WW3 (2D spectra in netcdf format only - LBCWA=T).
                                         ! 6 ~ WW3 2D spectra in netcdf format with LBCSP=T (prescribed spectra).
     FILEWAVE       = 'bndfiles.dat'     ! Boundary file defining boundary input from WW3
     LINDSPRDEG     = F                  ! If 1-d wave spectra are read this flag defines whether the input for the directional spreading is in degrees (true) or exponent (false)
     LPARMDIR       = F                  ! If LPARMDIR is true then directional spreading is read from WBDS and must be in exponential format at this time, only valid for 1d Spectra
                                         ! For WW3 boundary input also set LINHOM=T, LBCSE=T and this works only for spherical coordinates

     !Below are not used with WW3
     WBHS           = 2.                 ! Hs at the boundary for parametric spectra
     WBSS           = 2                  ! 1 or -1: Pierson-Moskowitz, 2 or -2: JONSWAP, 3 or -3: all in one BIN,
                                         ! 4: Gauss. The sign decides whether WBTP below is
                                         ! peak (+) or mean period (-)
     WBTP           = 8.                 ! Tp at the boundary (sec); mean or peak depending on the sign of WBSS
     WBDM           = 90.0               ! Avg. Wave Direction at the boundary
     WBDSMS         = 1                  ! Directional spreading value in degrees (1) or as exponent (2)
     WBDS           = 10.                ! Directional spreading at the boundary (degrees/exponent)
     WBGAUSS        = 0.1                ! factor for gaussian distribution if WBSS=1
                                         ! End section for LBCWA=T and LINHOM=F
     WBPKEN         = 3.3                ! Peak enhancement factor for Jonswap Spectra if WBSS=2
    ! NCDF_HS_NAME   = 'hs'               ! NETCDF var. name for the significant wave height (normally it is just 'hs')
    ! NCDF_DIR_NAME  = 'dir'              ! NETCDF var. name for the mean wave direction (normally it is just 'dir')
    ! NCDF_SPR_NAME  = 'spr'              ! NETCDF var. name for the mean directional spreading (normally it is just 'spr')
    ! NCDF_FP_NAME   = 'fp'               ! NETCDF var. name for the peak freq. (normally it is just 'fp')
    ! NCDF_F02_NAME  = 't02'              ! NETCDF var. name for the zero down crossing freq. (normally it is just 't02')
    /

    &WIND
    /

    &CURR
    /

    &WALV
    /


    &ENGS !SOURCE TERMS
     MESNL          = 1                  ! Nonlinear Interaction NL4 , 1 ~ on, 0 ~ off (Discrete Interaction approx.)
     MESIN          = 1                  ! Wind input: Ardhuin et al. (1) (use LSOURCESWAM = F);
                                         ! for ECMWF physics (2); Makin & Stam (3); Babanin et al. (4); Cycle 3 (5);
                                         !no wind (0). Try MESIN=1, LSOURCESWAM=F or MESIN=2 and LSOURCESWAM=T
     IFRIC          = 1                  ! Formulation for atmospheric boundary layer, (IFRIC = 1 for MESIN = 1, IFRIC = 4 for MESIN=3);
     MESBF          = 1                  ! Bottom friction: 1 - JONSWAP (Default); 2 - Madsen et al. (1989); 3 - SHOWEX
     FRICC          = 0.067              ! if MESBF=1: JONSWAP bottom friction coefficient [0.038,0.067]. If MESBF=2: physical bottom roughness (ignored if given in rough.gr3). If MESBF=3: D50 (if negative read from SHOWEX_D50.gr3)
     MESBR          = 1                  ! Shallow water wave breaking; 0: off; 1: on
     IBREAK         = 1                  ! Wave breaking formulation: 1 - Battjes and Janssen (1978)
                                         !                            2 - Thornton and Guza (1983) - Constant weighting function
                                         !                            3 - Thornton and Guza (1983) - Skewed weighting function
                                         !                            4 - van der Westhuysen (2010)
                                         !                            5 - Baldock et al (1998) modified by Janssen and Battjes (2007)
                                         !                            6 - Church and Thornton (1993)
     ICRIT          = 1                  ! Wave breaking criterion: 1   - Constant breaker index (gamma) or gamma_TG defined with BRCR
                                         !                          2,6 - gamma computed with local steepness adapted from Battjes and Stive (1985)
                                         !                          3   - Biphase threshold (intended for IBREAK=4)
                                         !                          4   - gamma_TG = a_BRCR * slope + b_BRCR / min_BRCR < gamma_TG < max_BRCR
                                         !                                e.g. Sallenger and Holman 1985
                                         !                          5   - gamma = a_BRCR * k_ph + b_BRCR / min_BRCR < gamma < max_BRCR
                                         !                                e.g. Ruessink et al (2003) with a_BRCR=0.76 and b_BRCR=0.29
     BRCR           = 0.78               ! either gamma, default is 0.73 for IBREAK=1,5 or gamma_TG, default is 0.42 for IBREAK=2,3 or biphase_ref, default is -4pi/9 = -1.3963 for IBREAK=4
     a_BRCR         = 0.76               ! cf ICRIT = 4, 5
     b_BRCR         = 0.29               ! cf ICRIT = 4, 5
     min_BRCR       = 0.25               ! cf ICRIT = 4, 5
     max_BRCR       = 0.8                ! cf ICRIT = 4, 5
     a_BIPH         = 0.2                ! Biphase coefficient, default 0.2 (intended for IBREAK=3)
     BR_COEF_METHOD = 1                  ! Method for the breaking coefficient: 1 - constant, 2 - adaptive
     B_ALP          = 0.5                  ! breaking coefficient. If BR_COEF_METHOD = 2, B_ALP ~ 40
     ZPROF_BREAK    = 2                  ! Vertical distribution function of wave breaking source term, only used in 3D run
                                         ! IS: side index, k: vertical layer index, dps: depth, zs: z vertical coordinate (/MSL), tmp0: Hs
                                         ! 1 - Homogeneous vertical distribution (swild_3D(k) = 1)
                                         ! 2 - swild_3D(k) = cosh((dps(IS)+zs(k,IS))/(0.2D0*tmp0))
                                         ! 3 - swild_3D(k) = 1.D0 - dtanh(((eta_tmp-zs(k,IS))/(0.5D0*tmp0))**2.D0)
                                         ! 4 - swild_3D(k) = 1.D0 - dtanh(((eta_tmp-zs(k,IS))/(0.5D0*tmp0))**4.D0)
                                         ! 5 - swild_3D(k) = 1.D0 - dtanh(((eta_tmp-zs(k,IS))/(0.5D0*tmp0))**8.D0)
                                         ! 6 - Sink of momentum applied in the two surface layers (IF (k .GE. NVRT-1) swild_3D(k)=1.D0)
     BC_BREAK       = 1                  ! Apply depth-limited breaking at the boundaries: 1 - On; 0 - Off
     IROLLER        = 0                  ! Wave roller model (e.g., see Uchiyama et al., 2010): 1 - On; 0 - Off; not used at the moment
     ALPROL         = 0.85               ! Alpha coefficient for the wave roller model (between 0 and 1): 1 - full conversion; 0 - no energy transferred to the roller
     MEVEG          = 0                  ! Vegetation on/off. If on, isav must = 1 in param.nml
     LMAXETOT       = T                  ! Limit shallow water wave height by wave breaking limiter (default=T)
     MESDS          = 1                  ! Formulation for the whitecapping source function; same value as MESIN
     MESTR          = 1                  ! Formulation for the triad 3 wave interactions (MESTR = 0 (off), MESTR = 1 (Lumped Triad Approx. (LTA)), MESTR = 2 (corrected version of LTA by Salmon et al. (2016)))
     TRICO          = 0.1                ! proportionality const. (\alpha_EB); default is 0.1
     TRIRA          = 2.5                ! ratio of max. freq. considered in triads over mean freq.; 2.5 is suggested
     TRIURS         = 0.1                ! critical Ursell number; if Ursell # < TRIURS; triads are not computed
    /

    &NUMS
     ICOMP          = 3
                                         ! This parameter controls the way how the splitting is done and whether implicit or explicit schemes are used for spectral advection
                                         ! ICOMP = 0
                                         ! This means that all dimensions are integrated using explicit methods. Similar
                                         ! to WW3, actually the same schemes are available in WW3 4.1.
                                         ! ICOMP = 1
                                         ! This mean that advection in geographical space is done using implicit
                                         ! Methods, source terms and spectral space are still integrated as done in
                                         ! WW3.
                                         ! ICOMP = 2
                                         ! This means that the advection is done using implicit methods and that the
                                         ! source terms are integrated semi-implicit using Patankar rules and linearized
                                         ! source terms as done in SWAN. Spectral part is still a fractional step
                                         ! ICOMP = 3: fully implicit and no splitting

     AMETHOD        = 7
                                         ! AMETHOD controls the different Methods in geographical space
                                         ! AMETHOD = 0
                                         ! No Advection in geo. Space
                                         ! AMETHOD = 1
                                         ! Explicit N-Scheme for ICOMP = 0 and Implicit N-Scheme for ICOMP > 0
                                         ! AMETHOD = 2
                                         ! PSI-Scheme for ICOMP = 0 and Implicit
                                         ! Crank-Nicholson N-Scheme for ICOMP > 0
                                         ! AMETHOD = 3
                                         ! LFPSI Scheme for ICOMP = 0 and Implicit two time level N2 scheme for ICOMP > 0

                                         ! AMETHOD = 4
                                         ! Like AMETHOD = 1 but using PETSc based on small matrices MNP**2. this can be efficient on small to medium scale cluster up to say 128 Nodes.

                                         ! AMETHOD = 5
                                         ! Like AMETHOD = 1 but using PETSc and assembling the full matrix and the source terms at once (MNP * MDC * MSC)**2. number of equations
                                         ! this is for large scale applications

                                         ! Remark for AMETHOD = 4 and 5. This methods are new and only tested on a few cases where the results look reasonable and do not depend on the number of CPU's which
                                         ! validates the correct implementation. The scaling performance is anticipated to be "quite poor" at this time. Many different constituents influence the parallel speedup.
                                         ! Please let me know all the information you have in order to improve and accelerate the development of implicit parallel WWM-III.
                                         ! Have fun ... Aron and Thomas.
                                         ! AMETHOD = 6 - BCGS Solver
                                         ! AMETHOD = 7 - GAUSS and JACOBI SOLVER
     SMETHOD        = 1
                                         ! This switch controls the way the source terms are integrated. 0: no source terms;
                                         ! 1: splitting using RK-3 and SI for fast and slow modes 2: semi-implicit;
                                         ! 3: R-K3 (if ICOMP=0 or 1) - slow; 4: Dynamic Splitting (experimental)
                                         ! 6: Sub-time steps for breaking term integration (subroutine INT_SHALLOW_SOURCETERMS), to enhance stability in surf zone if explicit method is used

     DMETHOD        = 2
                                         ! This switch controls the numerical method in directional space.
                                         ! DMETHOD = 0
                                         ! No advection in directional space
                                         ! DMETHOD = 1
                                         ! Crank-Nicholson (RTHETA = 0.5) or Euler Implicit scheme (RTHETA = 1.0)
                                         ! DMEHOD = 2
                                         ! Ultimate Quickest as in WW3 (usually best)
                                         ! DMETHOD = 3
                                         ! RK5-WENO
                                         ! DMETHOD = 4
                                         ! Explicit FVM Upwind scheme
     RTHETA         = 0.5                ! Weighing factor for DMETHOD = 1, not really useful since Crank Nicholson integration can only be monotone for CFL .le. 2
     LITERSPLIT     = F                  ! T: double Strang split; F: simple split (more efficient). Default: F

     LFILTERTH      = F
                                         ! LFILTERTH: use a CFL filter to limit the advection vel. In directional space. This is similar to WW3.
                                         ! Mostly not used. WWMII is always stable.
     MAXCFLTH       = 1.0                ! Max Cfl in Theta space; used only if LFILTERTH=T
     FMETHOD        = 1
                                         ! This switch controls the numerical method used in freq. space
                                         ! = 0
                                         ! No Advection in spectral space
                                         ! = 1
                                         ! Ultimate Quickest as in WW3 (best)
     LFILTERSIG     = F                  ! Limit the advection velocity in freq. space (usually F)
     MAXCFLSIG      = 1.0                ! Max Cfl in freq. space; used only if LFILTERSIG=T
     LLIMT          = T                  ! Switch on/off Action limiter, Action limiter must mostly be turned on.

     MELIM          = 1                  ! Formulation for the action limiter
                                         ! MELIM = 1 (default)
                                         ! Limiter according to the WAM group (1988)
                                         ! MELIM = 2
                                         ! Limiter according to Hersbach Janssen (1999)
                                         ! For MESIN = 1 and MESDS = 1, which represents Cycle 3 formulation or Ardhuin, or other formulations except Cycle4, use MELIM = 1 and LIMFAK = 0.1
                                         ! For MESIN = 2 and MESDS = 2, which represents Cycle 4 formulation, use MELIM = 3 and LIMFAK = 0.6

     LIMFAK         = 0.1                ! Proportionality coefficient for the action limiter MAX_DAC_DT = Limfak * Limiter; see notes above for value
     LDIFR          = F                  ! Use phase decoupled diffraction approximation according to Holthuijsen et al. (2003) (usually T; if crash, use F)
     IDIFFR         = 1                  ! Extended WAE accounting for higher order effects WAE becomes nonlinear; 1: Holthuijsen et al. ; 2: Liau et al. ; 3: Toledo et al. (in preparation)
     LCONV          = F                  ! Estimate convergence criterian and write disk (quasi-steady - qstea.out)
     LCFL           = F                  ! Write out CFL numbers; use F to save time
     NQSITER        = 1                  ! # of quasi-steady (Q-S) sub-divisions within each WWM time step (trial and errors)
     QSCONV1        = 0.98               ! Number of grid points [%/100] that have to fulfill abs. wave height criteria EPSH1
     QSCONV2        = 0.98               ! Number of grid points [%/100] that have to fulfill rel. wave height criteria EPSH2
     QSCONV3        = 0.98               ! Number of grid points [%/100] that have to fulfill sum. rel. wave action criteria EPSH3
     QSCONV4        = 0.98               ! Number of grid points [%/100] that have to fulfill rel. avg. wave steepness criteria EPSH4
     QSCONV5        = 0.98               ! Number of grid points [%/100] that have to fulfill avg. rel. wave period criteria EPSH5

     LEXPIMP        = F                  ! Use implicit schemes for freq. lower than given below by FREQEXP; used only if ICOMP=0
     FREQEXP        = 0.1                ! Minimum frequency for explicit schemes; only used if LEXPIMP=T and ICOMP=0
     EPSH1          = 0.01               ! Convergence criteria for rel. wave height ! EPSH1 < CONVK1 = REAL(ABS(HSOLD(IP)-HS2)/HS2)
     EPSH2          = 0.01               ! Convergence criteria for abs. wave height ! EPSH2 < CONVK2 = REAL(ABS(HS2-HSOLD(IP)))
     EPSH3          = 0.01               ! Convergence criteria for the rel. sum of wave action ! EPSH3 < CONVK3 = REAL(ABS(SUMACOLD(IP)-SUMAC)/SUMAC)
     EPSH4          = 0.01               ! Convergence criteria for the rel. avg. wave steepness criteria ! EPSH4 < CONVK4 = REAL(ABS(KHS2-KHSOLD(IP))/KHSOLD(IP))
     EPSH5          = 0.01               ! Convergence criteria for the rel. avg. waveperiod ! EPSH5 < REAL(ABS(TM02-TM02OLD(IP))/TM02OLD(IP))
     LVECTOR        = F                  ! Use optmized propagation routines for large high performance computers e.g. at least more than 128 CPU. Try LVECTOR=F first.
     IVECTOR        = 2                  ! USed if LVECTOR=T; Different flavours of communications
                                         ! LVECTOR = 1; same propagation style as if LVECTOR = F, this is for testing and development
                                         ! LVECTOR = 2; all spectral bins are propagated with the same time step and communications is done only once per sub-iteration
                                         ! LVECTOR = 3; all directions with the same freq. are propagated using the same time step the communications is done for each freq.
                                         ! LVECTOR = 4; 2 but for mixed open-mpi, code has to be compiled with -openmp
                                         ! LVECTOR = 5; 3 but for mixed open-mpi, code has to be compiled with -openmp
                                         ! LVECTOR = 6; same as 2 but highly optimized with respect to memory usage, of course it is must less efficient than 2
                                         ! remarks: if you are using this routines be aware that the memory amount that is used is approx. for LVECTOR 1-5 around
                                         ! 24 * MSC * MDC * MNP, so if you are trying this on 1 CPU you get a segmentation fault if your system has not enough memory or
                                         ! if your system is not properly configured it may results into the fact that your computer starts blocking since it try's to swap to disk
                                         ! The total amount of memory used per CPU = 24 * MSC * MDC * MNP / No.CPU
     LADVTEST       = F                  ! for testing the advection schemes, testcase will be added soon
     LCHKCONV       = F                  ! needs to set to .true. for quasi-steady mode. in order to compute the QSCONVi criteria and check them
     DTMIN_DYN      = 1.                 ! min. time step (sec?) for dynamic integration, this controls in SMETHOD the smallest time step for the triads, DT = 1.s is found to work well.
     NDYNITER       = 100,               ! max. iteration for dyn. scheme afterwards the limiter is applied in the last step, for SMETHOD .eq. this controls the integration of the triad interaction terms, which is done dynamically.
     DTMIN_SIN      = 1.                 ! min. time steps for the full fractional step method, where each source term is integrated with its own fractional step
     DTMIN_SNL4     = 1.                 !
     DTMIN_SDS      = 1.                 !
     DTMIN_SNL3     = 1.                 !
     DTMIN_SBR      = 0.10               !
     DTMIN_SBF      = 1.0                !
     NDYNITER_SIN   = 10,       	     ! max. iterations for each source term in the fractional step approach.
     NDYNITER_SNL4  = 10,       	     !
     NDYNITER_SDS   = 10,       	     !
     NDYNITER_SBR   = 10,        	     !
     NDYNITER_SNL3  = 10,       	     !
     NDYNITER_SBF   = 10,        	     !
     LSOUBOUND      = F                  ! Do source terms on boundary, this is possible as long only dissipative processes are governing the spectral evolution, otherwise, with wind u will get the max. possible wave height
                                         ! based on infinie fetch ... good for harbor studies. This is efficiently used for flume experiemnts mostly since in this case one would get a gradient in the crossection due to the effect
                                         ! that source terms are not treated there.
                                         ! 1: use PETSC
     WAE_SOLVERTHR =  1.e-6,             ! Threshold for the Block-Jacobi or Block-Gauss-Seider solver
     MAXITER =         1000,              ! Max. number of iterations
     PMIN    =  1.,                      ! Max. percentage of non-converged grid points
     LNANINFCHK      = F,                ! Check for NaN and INF; usually turned off for efficiency
     LZETA_SETUP     = F,                ! Compute wave setup (simple momentum eq.)
     ZETA_METH       = 0,                ! Method for wave setup, Mathieu please explain!
     LSOURCESWAM     = F,                ! Use ECMWF WAM formualtion for deep water physics.
    ! LSOURCESWWIII   = F,                ! WW3 Ardhuin et al. sources, not working yet in this code- use MESIN=1
     BLOCK_GAUSS_SEIDEL = T,             ! Use the Gauss Seidel on each
                                         ! computer block. The result seems
                                         ! to be faster and use less memory
                                         ! But the # of iterations depends on the
                                         ! number of processors
     LNONL   = F                         ! Solve the nonlinear system using simpler algorithm (Patankar)
     ASPAR_LOCAL_LEVEL = 0               ! Aspar locality level
                                         ! 0 ASPAR_JAC(MSC,MDC,MNP),
                                         ! CAD_THE(MSC,MDC,MNP), CAS_SIG(MSC,MDC,MNP)
                                         ! are allocated
                                         ! 1: only ASPAR_JAC
                                         ! 2: only small local arrays.
                                         ! 3: more local
                                         ! 4: mathieu magic 1
                                         ! 5: mathieu magic 2
     L_SOLVER_NORM = F                   ! Compute solver norm ||A*x-b|| as termination
                                         ! check of jacobi-Gauss-Seidel solver. Will increas cost if T
     LACCEL  = F
    /


    ! output of statistical variables over the whole domain at specified times.
    &HISTORY
     BEGTC          = '20030908.000000'  ! Start output time, yyyymmdd. hhmmss;
                                         ! must fit the simulation time otherwise no output.
                                         ! Default is same as PROC%BEGTC
     DELTC          = 1  ! Time step for output; if smaller than simulation time step, the latter is used (output every step for better 1D 2D spectra analysis)
     UNITC          = 'SEC'              ! Unit
     ENDTC          = '20031008.000000'  ! Stop time output, yyyymmdd. hhmmss
                                         ! Default is same as PROC%ENDC
     DEFINETC       = 86400              ! Time scoop (sec) for history files
                                         ! If unset or set to a negative value
                                         ! then only one file is generated
                                         ! otherwise, for example for 86400
                                         ! daily output files are created.
     OUTSTYLE       = 'NO'              ! output option - use 'NO' for no output
                                         ! 'NC' for netcdf output
                                         ! 'XFN' for XFN output (default)
                                         ! 'SHP' for DARKO SHP output
     MULTIPLEOUT      = 0                ! 0: output in a single netcdf file
                                         !    MPI_reduce is used (default)
                                         ! 1: output in separate netcdf files
                                         !    each associated with one process
     USE_SINGLE_OUT  = T                 ! T: Use single precision in the
                                         !    output of model variables (default)
     PARAMWRITE      = T                 ! T: Write the physical parametrization
                                         !    and chosen numerical method
                                         !    in the netcdf file (default T)
     GRIDWRITE       = T                 ! T/F: Write the grid in the netcdf history file (default T)
     PRINTMMA        = F                 ! T/F: Print minimum, maximum and average
                                         ! value of statistics during runtime
                                         ! (Default F)
                                         ! (Requires a MPI_REDUCE)
     FILEOUT        = 'wwm_hist.dat'
                                         ! Below is selection for all variables. Default is F for all variables.
     HS             = F                  ! significant wave height
     TM01           = F                  ! mean period
     TM02           = F                  ! zero-crossing mean period
     KLM            = F                  ! mean wave number
     WLM            = F                  ! mean wave length
     ETOTC          = F                  ! Variable ETOTC
     ETOTS          = F                  ! Variable ETOTS
     DM             = F                  ! mean wave direction
     DSPR           = F                  ! directional spreading
     TPPD           = F                  ! direaction of the peak ... check source code
     TPP            = F                  ! peak period
     CPP            = F                  ! peak phase vel.
     WNPP           = F                  ! peak wave number
     CGPP           = F                  ! peak group speed
     KPP            = F                  ! peak wave number
     LPP            = F                  ! peak wave length
     PEAKD          = F                  ! peak direction
     PEAKDSPR       = F                  ! peak directional spreading
     DPEAK          = F                  ! peak direction
     UBOT           = F                  ! bottom exc. vel.
     ORBITAL        = F                  ! bottom orbital vel.
     BOTEXPER       = F                  ! bottom exc.
     TMBOT          = F                  ! bottom period
     URSELL         = F                  ! Ursell number
     UFRIC          = F                  ! air friction velocity
     Z0             = F                  ! air roughness length
     ALPHA_CH       = F                  ! Charnoch coefficient for air
     WINDX          = F                  ! Wind in X direction
     WINDY          = F                  ! Wind in Y direction
     CD             = F                  ! Drag coefficient
     CURRTX         = F                  ! current in X direction
     CURRTY         = F                  ! current in Y direction
     WATLEV         = F                  ! water level
     WATLEVOLD      = F                  ! water level at previous time step
     DEPDT          = F                  ! change of water level in time
     DEP            = F                  ! depth
     TAUW           = F                  ! surface stress from the wave
     TAUHF          = F                  ! high frequency surface stress
     TAUTOT         = F                  ! total surface stress
     STOKESSURFX    = F                  ! Surface Stokes drift in X direction
     STOKESSURFY    = F                  ! Surface Stokes drift in X direction
     STOKESBAROX    = F                  ! Barotropic Stokes drift in X direction
     STOKESBAROY    = F                  ! Barotropic Stokes drift in Y direction
     RSXX           = F                  ! RSXX potential of LH
     RSXY           = F                  ! RSXY potential of LH
     RSYY           = F                  ! RSYY potential of LH
     CFL1           = F                  ! CFL number 1
     CFL2           = F                  ! CFL number 2
     CFL3           = F                  ! CFL number 3
    /

    &STATION
     BEGTC          = '20030908.000000'  ! Start simulation time, yyyymmdd. hhmmss; must fit the simulation time otherwise no output
                                         ! Default is same as PROC%BEGTC
     DELTC          = 600                ! Time step for output; if smaller than simulation time step, the latter is used (output every step for better 1D 2D spectra analysis)
     UNITC          = 'SEC'              ! Unit
     ENDTC          = '20031008.000000'  ! Stop time simulation, yyyymmdd. hhmmss
                                         ! Default is same as PROC%ENDC
     DEFINETC       = 86400              ! Time for definition of station files
                                         ! If unset or set to a negative value
                                         ! then only one file is generated
                                         ! otherwise, for example for 86400
                                         ! daily output files are created.
     OUTSTYLE       = 'NO'               ! output option
                                         ! 'NO' no output
                                         ! 'STE' classic station output (default)
                                         ! 'NC' for netcdf output
     MULTIPLEOUT      = 0                ! 0: output in a single netcdf file
                                         !    MPI_reduce is used (default)
                                         ! 1: output in separate netcdf files
                                         !    each associated with one process
     USE_SINGLE_OUT  = T                 ! T: Use single precision in the
                                         !    output of model variables (default)
     PARAMWRITE      = T                 ! T: Write the physical parametrization
                                         !    and chosen numerical method
                                         !    in the netcdf file (default T)
     FILEOUT        = 'wwm_sta.dat'      !not used
     LOUTITER       = F
     IOUTS   =          15,
     NOUTS   = 'P-1', 'P-2', 'P-3', 'P-4', 'P-5', 'P-6', 'P-7', 'P-8', 'P-9', 'P-10', 'P-11', 'P-12', 'P-13', 'P-14', 'P-15'
     XOUTS  =   -76.0460000000000     ,  -76.7780000000000     ,  -75.8100000000000     ,  -75.7200000000000     ,  -74.8420000000000     ,
       -74.7030000000000     ,  -75.3300000000000     ,  -72.6310000000000     ,  -74.8350000000000     ,  -69.2480000000000     ,
       -72.6000000000000
     YOUTS   =   39.152, 38.556,  38.033,   37.551,
        36.9740000000000     ,   37.2040000000000     ,   37.0230000000000     ,   36.9150000000000     ,   36.6110000000000     ,
        38.4610000000000     ,   35.7500000000000     ,   34.5610000000000     ,   31.8620000000000     ,   40.5030000000000     ,
        39.5840000000000
     CUTOFF         = 15*0.44            ! cutoff freq (Hz) for each station - consistent with buoys
     LSP1D          = T                  ! 1D spectral station output
     LSP2D          = F                  ! 2D spectral station output
     LSIGMAX        = T                  ! Adjust the cut-freq. for the output (e.g. consistent with buoy cut-off freq.)
     AC             = F                  ! spectrum
     WK             = F                  ! variable WK
     ACOUT_1D       = F                  ! variable ACOUT_1D
     ACOUT_2D       = F                  ! variable ACOUT_2D
     HS             = F                  ! significant wave height
     TM01           = F                  ! mean period
     TM02           = F                  ! zero-crossing mean period
     KLM            = F                  ! mean wave number
     WLM            = F                  ! mean wave length
     ETOTC          = F                  ! Variable ETOTC
     ETOTS          = F                  ! Variable ETOTS
     DM             = F                  ! mean wave direction
     DSPR           = F                  ! directional spreading
     TPPD           = F                  ! Discrete Peak Period
     TPP            = F                  ! Peak Period
     CPP            = F
     WNPP           = F                  ! peak wave number
     CGPP           = F                  ! peak group speed
     KPP            = F                  ! peak wave number
     LPP            = F                  ! peak
     PEAKD          = F                  ! peak direction
     PEAKDSPR       = F                  ! peak directional spreading
     DPEAK          = F
     UBOT           = F
     ORBITAL        = F
     BOTEXPER       = F
     TMBOT          = F
     URSELL         = F                  ! Ursell number
     UFRIC          = F                  ! air friction velocity
     Z0             = F                  ! air roughness length
     ALPHA_CH       = F                  ! Charnoch coefficient for air
     WINDX          = F                  ! Wind in X direction
     WINDY          = F                  ! Wind in Y direction
     CD             = F                  ! Drag coefficient
     CURRTX         = F                  ! current in X direction
     CURRTY         = F                  ! current in Y direction
     WATLEV         = F                  ! water level
     WATLEVOLD      = F                  ! water level at previous time step
     DEPDT          = F                  ! change of water level in time
     DEP            = F                  ! depth
     TAUW           = F                  ! surface stress from the wave
     TAUHF          = F                  ! high frequency surface stress
     TAUTOT         = F                  ! total surface stress
     STOKESSURFX    = F                  ! Surface Stokes drift in X direction
     STOKESSURFY    = F                  ! Surface Stokes drift in X direction
     STOKESBAROX    = F                  ! Barotropic Stokes drift in X direction
     STOKESBAROY    = F                  ! Barotropic Stokes drift in Y direction
     RSXX           = F                  ! RSXX potential of LH
     RSXY           = F                  ! RSXY potential of LH
     RSYY           = F                  ! RSYY potential of LH
     CFL1           = F                  ! CFL number 1
     CFL2           = F                  ! CFL number 2
     CFL3           = F                  ! CFL number 3
    /

    &HOTFILE
     LHOTF          = T                  ! Write hotfile
     FILEHOT_OUT    = 'hotfile_out_WWM.nc'      !name of output
     BEGTC          = '20030908.000000'  !Starting time of hotfile writing. With ihot!=0 in SCHISM,
                                         !this will be whatever the new hotstarted time is (even with ihot=2)
     DELTC          = 86400.             ! time between hotfile writes
     UNITC          = 'SEC'              ! unit used above
     ENDTC          = '20031008.000000'  ! Ending time of hotfile writing (adjust with BEGTC)
     LCYCLEHOT      = T                  ! Applies only to netcdf
                                         ! If T then hotfile contains 2 last records (1st is the most recent).
                                         ! If F then hotfile contains N record if N outputs
                                         ! have been done
                                         ! For binary only one record.
     HOTSTYLE_OUT   = 2                  ! 1: binary hotfile of data as output
                                         ! 2: netcdf hotfile of data as output (default)
     MULTIPLEOUT    = 0                  ! 0: hotfile in a single file (binary or netcdf)
                                         !  MPI_REDUCE is then used and thus you'd avoid too freq. output
                                         ! 1: hotfiles in separate files, each associated
                                         ! with one process

     !Input part: to use WWM input, need to turn on LHOTR in &INIT!
     FILEHOT_IN     = 'hotfile_in_WWM.nc'    ! (Full) hot file name for input (which can be copied from FILEHOT_OUT above)
     HOTSTYLE_IN    = 2                  ! 1: binary hotfile of data as input
                                         ! 2: netcdf hotfile of data as input (default)
     IHOTPOS_IN     = 1                  ! Position in hotfile (only for netcdf)
                                         ! for reading. If LCYCLEHOT=T, this can be 1 or 2 (out of the 2 time records). '1' is the most recent time.
     MULTIPLEIN     = 0                  ! 0: read hotfile from one single file
                                         ! 1: read hotfile from multiple files (must use same # of CPU?)
    /

    ! only used with AMETHOD 4 or 5
    &PETScOptions
                                         ! Summary of Sparse Linear Solvers Available from PETSc: http://www.mcs.anl.gov/petsc/documentation/linearsolvertable.html
     KSPTYPE       = 'LGMRES'
                                         ! This parameter controls which solver is used. This is the same as petsc command line parameter -ksp_type.
                                         ! KSPTYPE = 'GMRES'
                                         ! Implements the Generalized Minimal Residual method. (Saad and Schultz, 1986) with restart
                                         ! KSPTYPE = 'LGMRES'
                                         ! Augments the standard GMRES approximation space with approximations to the error from previous restart cycles.
                                         ! KSPTYPE = 'DGMRES'
                                         ! In this implementation, the adaptive strategy allows to switch to the deflated GMRES when the stagnation occurs.
                                         ! KSPTYPE = 'PGMRES'
                                         ! Implements the Pipelined Generalized Minimal Residual method. Only PETSc 3.3
                                         ! KSPTYPE = 'KSPBCGSL'
                                         ! Implements a slight variant of the Enhanced BiCGStab(L) algorithm

     RTOL          = 1.E-20              ! the relative convergence tolerance (relative decrease in the residual norm)
     ABSTOL        = 1.E-20              ! the absolute convergence tolerance (absolute size of the residual norm)
     DTOL          = 10000.              ! the divergence tolerance
     MAXITS        = 1000                ! maximum number of iterations to use

     INITIALGUESSNONZERO = F             ! Tells the iterative solver that the initial guess is nonzero; otherwise KSP assumes the initial guess is to be zero
     GMRESPREALLOCATE    = T             ! Causes GMRES and FGMRES to preallocate all its needed work vectors at initial setup rather than the default, which is to allocate them in chunks when needed.


     PCTYPE        = 'SOR'
                                         ! This parameter controls which  preconditioner is used. This is the same as petsc command line parameter -pc_type
                                         ! PCTYPE = 'SOR'
                                         ! (S)SOR (successive over relaxation, Gauss-Seidel) preconditioning
                                         ! PCTYPE = 'ASM'
                                         ! Use the (restricted) additive Schwarz method, each block is (approximately) solved with its own KSP object.
                                         ! PCTYPE = 'HYPRE'
                                         ! Allows you to use the matrix element based preconditioners in the LLNL package hypre
                                         ! PCTYPE = 'SPAI'
                                         ! Use the Sparse Approximate Inverse method of Grote and Barnard as a preconditioner
                                         ! PCTYPE = 'NONE'
                                         ! This is used when you wish to employ a nonpreconditioned Krylov method.
    /

    &NESTING
    /
     ListBEGTC =''
     ListDELTC = ZERO
     ListUNITC =''
     ListENDTC =''
     ListIGRIDTYPE =0
     ListFILEGRID =''
     ListFILEBOUND =''
     ListPrefix =''
    /

    """

    proc: PROC = PROC()
    coupl: COUPL = COUPL()
    grid: GRID = GRID()
    init: INIT = INIT()
    hotfile: HOTFILE = HOTFILE()
    bouc: BOUC = BOUC()
    engs: ENGS = ENGS()
    nums: NUMS = NUMS()
    history: HISTORY = HISTORY()
    station: STATION = STATION()
    petscoptions: PETSCOPTIONS = PETSCOPTIONS()
    nesting: NESTING = NESTING()
