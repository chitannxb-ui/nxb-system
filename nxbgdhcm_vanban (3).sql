-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Máy chủ: 127.0.0.1
-- Thời gian đã tạo: Th5 20, 2026 lúc 11:18 AM
-- Phiên bản máy phục vụ: 12.2.2-MariaDB
-- Phiên bản PHP: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Cơ sở dữ liệu: `nxbgdhcm_vanban`
--

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `cau_hinh`
--

CREATE TABLE `cau_hinh` (
  `Person_key` varchar(255) NOT NULL,
  `Key_Name` varchar(255) NOT NULL,
  `Value` text DEFAULT NULL,
  `Description` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `deleted_documents`
--

CREATE TABLE `deleted_documents` (
  `md5` varchar(255) NOT NULL,
  `person_key` varchar(255) NOT NULL,
  `file_name` text DEFAULT NULL,
  `file_path` text DEFAULT NULL,
  `file_type` varchar(50) DEFAULT NULL,
  `doc_type` varchar(255) DEFAULT NULL,
  `doc_number` varchar(255) DEFAULT NULL,
  `doc_day` varchar(10) DEFAULT NULL,
  `doc_month` varchar(10) DEFAULT NULL,
  `doc_year` varchar(10) DEFAULT NULL,
  `doc_org` text DEFAULT NULL,
  `doc_signer` text DEFAULT NULL,
  `full_text` longtext DEFAULT NULL,
  `deleted_time` bigint(20) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `documents`
--

CREATE TABLE `documents` (
  `md5` varchar(255) NOT NULL,
  `person_key` varchar(255) NOT NULL,
  `file_name` text DEFAULT NULL,
  `file_path` text DEFAULT NULL,
  `file_type` varchar(50) DEFAULT NULL,
  `doc_type` varchar(255) DEFAULT NULL,
  `doc_number` varchar(255) DEFAULT NULL,
  `doc_day` varchar(10) DEFAULT NULL,
  `doc_month` varchar(10) DEFAULT NULL,
  `doc_year` varchar(10) DEFAULT NULL,
  `doc_org` text DEFAULT NULL,
  `doc_signer` text DEFAULT NULL,
  `full_text` longtext DEFAULT NULL,
  `summary` text DEFAULT NULL,
  `last_scan` bigint(20) DEFAULT NULL,
  `Fixed` tinyint(4) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `ket_noi_ai`
--

CREATE TABLE `ket_noi_ai` (
  `ID` int(11) NOT NULL,
  `person_key` varchar(255) DEFAULT NULL,
  `Preset_Name` varchar(255) DEFAULT NULL,
  `URL` varchar(500) DEFAULT NULL,
  `Model_Name` varchar(100) DEFAULT NULL,
  `API_Key` varchar(255) DEFAULT NULL,
  `Default` varchar(10) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `lich_su_ten_file`
--

CREATE TABLE `lich_su_ten_file` (
  `ID` int(11) NOT NULL,
  `Person_key` varchar(255) DEFAULT NULL,
  `MD5` varchar(255) DEFAULT NULL,
  `File_Path` text DEFAULT NULL,
  `Ten_Hien_Tai` text DEFAULT NULL,
  `Ten_Cu` text DEFAULT NULL,
  `Thoi_Diem` timestamp NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `loai_van_ban`
--

CREATE TABLE `loai_van_ban` (
  `ID` int(11) NOT NULL,
  `Loai_VB` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `Mo_ta` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Tu_khoa` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_uca1400_ai_ci;

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `nguoi_dung`
--

CREATE TABLE `nguoi_dung` (
  `Person_key` varchar(255) NOT NULL,
  `Mac_Address` varchar(100) DEFAULT NULL,
  `Computer_Name` varchar(255) DEFAULT NULL,
  `User_Name` varchar(255) DEFAULT NULL,
  `danh_xung` varchar(11) DEFAULT NULL,
  `Ho_Va_Ten` varchar(255) DEFAULT '',
  `Chuc_vu` varchar(255) DEFAULT '',
  `Phong_Ban` varchar(255) DEFAULT '',
  `Cong_tac` text DEFAULT NULL COMMENT 'Công việc đang được phân công',
  `NV_Phong` text DEFAULT NULL COMMENT 'Nhiệm vụ được giao của phòng',
  `Chuc_danh_khac` text DEFAULT NULL COMMENT 'Các chức danh kiêm nhiệm',
  `SYLL` longtext DEFAULT NULL COMMENT 'Sơ yếu lý lịch/Thông tin chi tiết'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `tach_file`
--

CREATE TABLE `tach_file` (
  `MD5` varchar(255) NOT NULL,
  `Trang` int(11) NOT NULL,
  `Toan_van` longtext DEFAULT NULL,
  `Nhan_xet` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `tao_van_ban`
--

CREATE TABLE `tao_van_ban` (
  `ID` int(11) NOT NULL,
  `Person_key` varchar(255) NOT NULL,
  `thoi_gian` datetime DEFAULT current_timestamp(),
  `ten_van_ban` varchar(500) DEFAULT NULL,
  `noi_dung` longtext DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Cấu trúc bảng cho bảng `van_ban_mau`
--

CREATE TABLE `van_ban_mau` (
  `id` int(11) NOT NULL,
  `Loai_Van_Ban` varchar(255) NOT NULL COMMENT 'Tên loại văn bản (vd: Tờ trình, Công văn, Hợp đồng)',
  `Ung_Dung` text DEFAULT NULL COMMENT 'Sơ lược về công dụng và trường hợp sử dụng',
  `Mo_Ta_Layout` longtext DEFAULT NULL COMMENT 'Mô tả chi tiết bố cục và cách trình bày bằng mã HTML',
  `Thanh_Phan_Tat_Yeu` text DEFAULT NULL COMMENT 'Danh sách các thông tin cần có, phân cách bằng dấu chấm phẩy',
  `Phòng_Ban_So_Huu` varchar(100) DEFAULT NULL COMMENT 'Phòng ban chịu trách nhiệm về mẫu này',
  `Ngay_Cap_Nhat` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Chỉ mục cho các bảng đã đổ
--

--
-- Chỉ mục cho bảng `cau_hinh`
--
ALTER TABLE `cau_hinh`
  ADD PRIMARY KEY (`Person_key`,`Key_Name`);

--
-- Chỉ mục cho bảng `deleted_documents`
--
ALTER TABLE `deleted_documents`
  ADD PRIMARY KEY (`md5`,`person_key`);

--
-- Chỉ mục cho bảng `documents`
--
ALTER TABLE `documents`
  ADD PRIMARY KEY (`md5`,`person_key`);
ALTER TABLE `documents` ADD FULLTEXT KEY `full_text` (`full_text`);

--
-- Chỉ mục cho bảng `ket_noi_ai`
--
ALTER TABLE `ket_noi_ai`
  ADD PRIMARY KEY (`ID`);

--
-- Chỉ mục cho bảng `lich_su_ten_file`
--
ALTER TABLE `lich_su_ten_file`
  ADD PRIMARY KEY (`ID`);

--
-- Chỉ mục cho bảng `loai_van_ban`
--
ALTER TABLE `loai_van_ban`
  ADD PRIMARY KEY (`ID`);

--
-- Chỉ mục cho bảng `nguoi_dung`
--
ALTER TABLE `nguoi_dung`
  ADD PRIMARY KEY (`Person_key`);

--
-- Chỉ mục cho bảng `tach_file`
--
ALTER TABLE `tach_file`
  ADD PRIMARY KEY (`MD5`,`Trang`);

--
-- Chỉ mục cho bảng `tao_van_ban`
--
ALTER TABLE `tao_van_ban`
  ADD PRIMARY KEY (`ID`);
ALTER TABLE `tao_van_ban` ADD FULLTEXT KEY `ten_van_ban` (`ten_van_ban`,`noi_dung`);

--
-- Chỉ mục cho bảng `van_ban_mau`
--
ALTER TABLE `van_ban_mau`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT cho các bảng đã đổ
--

--
-- AUTO_INCREMENT cho bảng `lich_su_ten_file`
--
ALTER TABLE `lich_su_ten_file`
  MODIFY `ID` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT cho bảng `loai_van_ban`
--
ALTER TABLE `loai_van_ban`
  MODIFY `ID` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT cho bảng `tao_van_ban`
--
ALTER TABLE `tao_van_ban`
  MODIFY `ID` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT cho bảng `van_ban_mau`
--
ALTER TABLE `van_ban_mau`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
